import string
import os

# the current directory of this file
def get_curr_dir():
    return os.path.dirname(os.path.realpath(__file__))

# some path originating from the current directory of this file
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

        for token in descriptor.split():
            if token == "Lesson":
                self.curr_info['L'] = 1  # either a lesson or activity
            elif token == "Pre-Board":
                self.curr_info['Pr'] = 1
            elif token == "Post-Board":
                self.curr_info['Po'] = 1
            elif token == "Example":
                self.curr_info['E'] = 1
            elif token[len(token) - 1].isdigit() and (len(token) == 1 or token[0] == '#'):
                self.curr_info['N'] = int(token[len(token) - 1])

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

# gets first (inclusive) and last (exclusive) index of operand characters
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

    # find the start of the expression
    further_bound : int = closer_bound
    if expression[closer_bound] == paren_plus:
        further_bound = closer_bound
        paren_count = 1  # becomes zero when full parenthesis expression has been closed
        # get to the end of the parenthesis statement
        while paren_count > 0:
            further_bound += shift_dir  # go in shift direction by one character
            curr_char = expression[further_bound]
            if curr_char == paren_plus: paren_count += 1
            if curr_char == paren_minus: paren_count -= 1

        if is_after: operand_end = further_bound
        else: further_bound = further_bound
    else:
        # find the end of the expression furthest from the operand
        if is_after:
            while further_bound < len(expression):
                further_bound += 1
                curr_char = expression[further_bound]
                if is_whitespace(curr_char) or is_operand(curr_char): break
        else:
            while further_bound >= 0:
                further_bound -= 1
                curr_char = expression[further_bound]
                if is_whitespace(curr_char) or is_operand(curr_char): break

    if is_after:
        return [closer_bound, further_bound]
    else:
        # further bound is one too far left to be inclusive and closer is one too far left to be exclusive
        return [further_bound + 1, closer_bound + 1]

# converts x^y to pow(x, y)
def update_pow_expr(expression : str):
    # update the format to match what is desired
    pow_index = expression.find('^')
    base_bounds : list[int] = get_operand_bounds(expression, pow_index, False)
    power_bounds : list[int] = get_operand_bounds(expression, pow_index, True)

    base : str = expression[base_bounds[0] : base_bounds[1]]
    power : str = expression[power_bounds[0] : power_bounds[1]]
    operation = "pow(" + base + ", " + power + ")"

    # strip out the power,
    return expression[0 : base_bounds[0]] + operation + expression[power_bounds[1] : len(expression)]

def update_pow_expressions(expression : str):
    # continue to perform replacement on all power expressions until they are replaced
    pow_index = expression.find('^')
    while pow_index > -1:
        expression = update_pow_expr(expression)
        pow_index = expression.find('^')

    return expression

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