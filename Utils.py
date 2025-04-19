import string
import os
from lxml import etree
from copy import deepcopy


def prettyprint(element, **kwargs):
    xml = etree.tostring(element, pretty_print=True, **kwargs)
    print(xml.decode(), end='')


def insert_text_element(container, name, text):
    # create and set values
    text_element = etree.SubElement(container, "value", {"name" : name})
    element_type = etree.SubElement(text_element, "block", {"type" : "text"})
    etree.SubElement(element_type, "field", {"name" : "TEXT"}).text = text

    return text_element


def update_expression_container(container : etree.Element) -> tuple[bool, str]:
    # text combination handling more complicated
    num_slots = int(container[0].attrib["items"])  # the slots available
    filled_slots = 0
    variables: dict[int, etree.Element] = {}  # the slots actually filled
    result_text = ""  # the result of combining all variables and text
    print("\nContainer start: \n")
    prettyprint(container)

    # elements in expression addition are 0 indexed
    for i in range(0, num_slots):
        potential_elements = container.xpath("./*[local-name()='value' and @name='ADD" + str(i) + "']")
        if potential_elements is None or len(potential_elements) == 0: continue
        curr_element = potential_elements[0]

        filled_slots += 1

        # if this isn't text, we will just treat it as a variable to re-insert after
        if curr_element[0] is None or curr_element[0].attrib["type"] != "text":
            variables[i] = deepcopy(curr_element)
            result_text += "ARG{" + str(i) + "}"  # we index based on the index assigned in xml
            continue

        # add the text from this element
        result_text += curr_element[0][0].text

    parsed_expressions : str = "    " + result_text
    print("Inspecting " + result_text + "\n")

    if result_text.find("^") == -1 and result_text.find("pow") == -1: return False, parsed_expressions  # no power to update
    prev_text = result_text
    result_text = update_pow_expressions(result_text)
    if prev_text == result_text: return False, parsed_expressions  # no fixup needed
    parsed_expressions += " -> " + result_text  # indicate update for logging

    # locate all arguments in the updated expression
    variable_infos: list[list[int]] = []  # store the arg index and start and end char indices
    arg_pos = result_text.find("ARG")
    while arg_pos != -1:
        arg_num_start = result_text.find("{", arg_pos + 3)
        arg_num_end = result_text.find("}", arg_pos + 3)
        variable_infos.append([int(result_text[arg_num_start + 1: arg_num_end]), arg_pos, arg_num_end])
        arg_pos = result_text.find("ARG", arg_num_end + 1)

    # split the result text
    text_elements: list[str] = []
    text_start = 0
    for variable_info in variable_infos:
        if text_start >= variable_info[1] - 1:
            # these are two back to back variables or a variable at the start
            text_start = variable_info[2] + 1
            continue
        text_elements.append(result_text[text_start: variable_info[1]])
        text_start = variable_info[2] + 1  # after argument portion is over, text begins again

    # we need to grab the very last text
    if text_start < len(result_text):
        text_elements.append(result_text[text_start : len(result_text)])

    # purge all elements other than the mutation
    for i in range(1, filled_slots + 1):
        # as we remove elements, subsequent ones have their index lowered
        container.remove(container[1])

    # set the exact number of elements needed
    filled_slots = len(text_elements) + len(variable_infos)
    container[0].set("items", str(filled_slots))

    # insert all elements in order
    element_count: int = 0
    var_count : int = 0

    # if we start with a variable instead of text, insert it first
    if len(variable_infos) > 0 and variable_infos[0][1] == 0:
        var = variables[variable_infos[var_count][0]]
        var.set("name", "ADD" + str(element_count))
        container.append(var)
        var_count += 1
        element_count += 1

    for text_element in text_elements:
        # first insert the text, then the variable that proceeds it
        insert_text_element(container, "ADD" + str(element_count), text_element)

        if element_count == filled_slots - 1: continue  # if we are one less than full, this was last element

        # put the next element, since they are stored in L->R order in variable_infos
        var = variables[variable_infos[var_count][0]]
        var.set("name", "ADD" + str(element_count + 1))
        container.append(var)

        element_count += 2
        var_count += 1

    print("\nContainer end: \n")
    prettyprint(container)
    print("\nUpdated to " + result_text + "\n")
    return True, parsed_expressions

# the current directory of this file
def get_curr_dir():
    return os.path.dirname(os.path.realpath(__file__))

# some path originating from the current directory of this file
# only ended with a separator if the last argument is empty or ends with one already
def append_cur_dir(*suffix : str):
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), *suffix)

# returns the id of the indicated board
def get_board_id(is_preboard : bool):
    if is_preboard: return "preBoard"
    return "postBoard"

class LinkInfo:
    def __init__(self, descriptor : str):
        self.curr_info: dict[str, int] = {
            "L": 0,
            "Pr": 0,
            "Po": 0,
            "E": 0,  # because solutions and examples always come with numbers, if N == 0
            "N": 0  # indicates no number provided
        }

        prev_token : str = ""
        for token in descriptor.split():
            if len(token) < 1: continue  # ignore empty tokens
            if token.find("Lesson") != -1:
                self.curr_info['L'] = 1  # either a lesson or activity
            elif token.find("Pre-Board") != -1:
                self.curr_info['Pr'] = 1
            elif token.find("Post-Board") != -1:
                self.curr_info['Po'] = 1
            elif token.find("Example") != -1:
                self.curr_info['E'] = 1
            # checks if token is preceded by Example or Solution, e.g. Example 2, or Solution #4
            elif prev_token.find("Example") != -1 or prev_token.find("Solution") != -1:
                # ensures numerical token is of form #xxxx... or 1, 2, 3, etc (assumes we never get numbers past 9
                if (token[0] == '#' and len(token) > 1 and token[1].isdigit()) or (token[0].isdigit() and len(token) == 1):
                    self.curr_info['N'] = int(token[len(token) - 1])

            prev_token = token

    def __str__(self):
        result : str = ""
        if self.is_lesson(): result += "Lesson "

        if self.is_example(): result += "Example "
        if self.has_num(): result += self.get_num_str() + " "

        if self.is_pre(): result += "Pre-Board"
        elif self.is_post(): result += "Post-Board"

    def is_lesson(self):
        return bool(self.curr_info['L'])

    def is_pre(self):
        return bool(self.curr_info['Pr'])

    def is_post(self):
        return bool(self.curr_info['Po'])

    def is_example(self):
        return bool(self.curr_info['E'])

    def has_num(self):
        return bool(self.curr_info['N'])

    def get_num_str(self):
        if self.has_num(): return str(self.curr_info['N'])
        return None  # if there was no number given we want to return None

def is_whitespace(char):
    return string.whitespace.__contains__(char)

def is_operand(char):
    operands = ['+', '-', '*', '/']
    return operands.__contains__(char)

def is_numerical(char):
    return '0' <= char <= '9' or char == '.'

# gets first (inclusive) and last (inclusive) index of operand characters
def get_operand_bounds(expression : str, op_index : int, is_after):
    # skip over whitespaces before power operator
    closer_bound : int = op_index  # will end on first non-whitespace character

    # determine if we are going up or down (past or before) in expression relative to op
    shift_dir = 0
    paren_plus = None
    paren_minus = None
    if is_after:
        # if we want following operand, it has the form: OP ( ... ), or: OP xxxx
        shift_dir = 1
        paren_plus = '('
        paren_minus = ')'
    else:
        # if we want preceding operand, it has form: ( ... ) OP, or: xxxx OP
        shift_dir = -1
        paren_plus = ')'
        paren_minus = '('

    closer_bound += shift_dir

    # find the first non whitespace index
    while is_whitespace(expression[closer_bound]):
        closer_bound += shift_dir

    # find the further end point of the expression
    further_bound : int = closer_bound
    has_paren : int = 0  # effectively a bool
    if expression[closer_bound] == paren_plus:
        has_paren = 1
        paren_count = 1  # becomes zero when full parenthesis expression has been closed
        # get to the end of the parenthesis statement
        while paren_count > 0:
            further_bound += shift_dir  # go in shift direction by one character
            curr_char = expression[further_bound]
            if curr_char == paren_plus: paren_count += 1
            if curr_char == paren_minus: paren_count -= 1
    else:
        # find the end of the expression furthest from the operand
        # these bounds ensure we won't do any shifting if we are already at edge
        while 0 < further_bound < len(expression) - 1:
            further_bound += shift_dir
            curr_char = expression[further_bound]
            if not is_numerical(curr_char):
                further_bound -= shift_dir  # go back to last valid character
                break

    if is_after:
        return [closer_bound, further_bound, has_paren]
    else:
        # further bound is one too far left to be inclusive and closer is one too far left to be exclusive
        return [further_bound, closer_bound, has_paren]

# converts x^y to pow(x, y)
def update_pow_expr(expression : str, pow_index):
    # update the format to match what is desired
    base_bounds : list[int] = get_operand_bounds(expression, pow_index, False)
    power_bounds : list[int] = get_operand_bounds(expression, pow_index, True)

    # if a parenthesis was used we can discard it
    # to do this we have it included in the replacement, but excluded from the expression
    base_lower = base_bounds[0] + base_bounds[2]
    base_upper = base_bounds[1] - base_bounds[2]

    pow_lower = power_bounds[0] + power_bounds[2]
    pow_upper = power_bounds[1] - power_bounds[2]

    base : str = expression[base_lower : base_upper + 1]
    power : str = expression[pow_lower : pow_upper + 1]

    operation = "pow(" + base + "," + power + ")"

    # strip out the power,
    return expression[0 : base_bounds[0]] + operation + expression[power_bounds[1] + 1 : len(expression)]

def update_pow_expressions(expression : str) -> str:
    # continue to perform replacement on all power expressions until they are replaced
    expression = inspect_pow_expressions(expression)

    pow_index = expression.find('^')
    while pow_index > -1:
        expression = update_pow_expr(expression, pow_index)
        pow_index = expression.find('^')

    return expression


def inspect_pow_expressions(expression : str) -> str:
    pow_index = expression.find("pow")
    while pow_index > -1:
        expression = inspect_pow_expr(expression, pow_index)
        pow_index = expression.find("pow", pow_index + 4)

    return expression


def inspect_pow_expr(expression : str, pow_index : int) -> str:
    arg_start = pow_index + 4
    paren_count = 1
    arg_end = arg_start
    for i in range(arg_start, len(expression)):
        curr_char : str = expression[i]
        if curr_char == '(': paren_count += 1
        elif curr_char == ')': paren_count -= 1

        if paren_count == 0:
            arg_end = i - 1
            break

    arg1_start = arg_start
    arg1_end = expression.find(",", arg_start) - 1
    arg2_start = arg1_end + 2
    arg2_end = arg_end

    arg1_paren_count = 0
    for i in range(arg1_start, arg2_start):
        curr_char : str = expression[i]
        if curr_char == '(': arg1_paren_count += 1
        elif curr_char == ')': arg1_paren_count -= 1

    arg2_paren_count = 0
    for i in range(arg2_start, arg2_end + 1):
        curr_char: str = expression[i]
        if curr_char == '(': arg2_paren_count += 1
        elif curr_char == ')': arg2_paren_count -= 1

    if arg1_paren_count + arg2_paren_count != 0:
        raise RuntimeError("Malformed power expression")

    # get the actual start of the first argument
    arg1_start_actual = arg1_start
    stripped_paren_count = 0
    for i in range(arg1_start, arg1_end + 1):
        if stripped_paren_count >= arg1_paren_count: break  # stop when we removed all extra paren
        curr_char : str = expression[i]
        if curr_char == '(': stripped_paren_count += 1
        arg1_start_actual += 1

    arg2_end_actual = arg2_end
    stripped_paren_count = 0
    for i in range(arg2_end, arg2_start - 1, -1):
        if stripped_paren_count >= arg1_paren_count: break
        curr_char : str = expression[i]
        if curr_char == ')': stripped_paren_count += 1
        arg2_end_actual -= 1

    # strip the parenthesis
    args_actual : str = expression[arg1_start_actual: arg2_end_actual + 1]
    args_actual.strip()  # remove whitespace on edges

    return expression[0 : arg_start] + args_actual + expression[arg_end + 1 : len(expression)]

def parse_out_links(location, separator):
    links: list[str] = []

    # get all the links as strings
    with open(location) as source:
        for line in source:
            if separator is None:
                links.append(line.strip())
                continue
            prev_sep_end = 0  # index at which we consider characters valid again (inclusive)
            next_sep = line.find(separator)
            while next_sep >= 0:
                links.append(line[prev_sep_end: next_sep])
                prev_sep_end = next_sep + len(separator)
                next_sep = line.find(separator, __start=prev_sep_end)

            # process last link with end line separator
            if prev_sep_end < len(separator):
                links.append(line[prev_sep_end: len(separator)])

    return links

def write_to_file(file_name, text):
    out_path = append_cur_dir(file_name)
    with open(out_path, 'a') as file:
        file.write(text)