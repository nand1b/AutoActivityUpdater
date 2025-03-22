import string
import traceback
from argparse import ArgumentParser
from time import sleep

from selenium.common import TimeoutException

from SeleniumUtils import *

def is_logged_in(driver):
    try:
        # locate socket connection status which only appears on login and see if its good
        connection_status = wait_for_vis(driver, "socketConnectionStatus", by_val=By.ID)
        if connection_status.get_attribute("class") != "fa fa-circle text-lime":
            raise ValueError("Connection status not good.")
    except Exception as error:
        return False

    return True

def ensure_logged_in(driver):
    print("Waiting for user to login...")
    while not is_logged_in(driver):
        sleep(3)
    print("User login detected.")

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

def update_models(driver, link, model):
    print("Beginning processing of: " + link)
    driver.get(link)
    # ensure_logged_in(driver)  # we can generally assume the user is already logged in

    # see if there is a popup prompt we need to get rid of
    try:
        prompt_close = wait_for_vis(driver, "//div[@class=\'jconfirm-buttons\']/button[text()=\'Close\']",
                              by_val=By.XPATH, timeout=1)
        prompt_close.click()
    except Exception as exception:
        print("No prompt found")

    # user should be logged in now
    robot_button = wait_for_vis(driver, "robotCollapseButton", by_val=By.ID)
    ActionChains(driver).scroll_to_element(robot_button)
    if robot_button.get_attribute("aria-expanded") == "false": robot_button.click()  # expand if not already

    # in case activity does not have robot (which happens surprisingly more than a few times)
    try:
        wait_and_get(driver, "//li[@class=\'robotItem relative \']", by_val=By.XPATH, timeout=1)
    except Exception as error:
        print("No robots in this activity; skipping")
        return

    robots = wait_for_viss(driver, "//li[@class=\'robotItem relative \']", by_val=By.XPATH)

    # set the models
    for index in range(0, len(robots)):
        print("Beginning on robot " + str(index + 1))
        robot = robots[index]  # they should be in order
        robot.find_element(By.TAG_NAME, "button").click()  # select robot

        # attempt to bypass opening model menu and associated issues of clickable image not loading
        # image = robot.find_element(by=By.CSS_SELECTOR, value="img")
        # model_path = "/img/models/" + model + ".png"
        # driver.execute_script("arguments[0].setAttribute(\"src\", \"" + model_path + "\")", image)

        wait_for_vis(driver, "robotModel" + str(index + 1), by_val=By.ID).click()  # open model selection
        image = wait_for_vis(driver, "//img[@value=\'" + model + "\']", 10, by_val=By.XPATH).click()  # select model
        wait_for_vis(driver, "closeButton", by_val=By.ID).click()  # close the menu
        print("Finished robot " + str(index + 1))

        # last line of robot processing
    print("Finished processing all robots; preparing to save.")
    robot_button.click()  # close the robot menu
    wait_for_vis(driver, "saveTab", by_val=By.ID).click()  # open the save menu

    try:
        # we try to quickly cause a throw if this is not a lesson
        wait_and_get(driver, "//div[@class=\'jconfirm-buttons\']/button[text()=\'Update Lesson\']",
                    by_val=By.XPATH, timeout=1)
        print("This is a lesson")
        goto_and_click(driver, "//div[@class=\'jconfirm-buttons\']/button[text()=\'Update Lesson\']",
                    by_val=By.XPATH, timeout=5)

    except Exception as error:
        print("This is an activity")
        goto_and_click(driver, "//div[@class=\'jconfirm-buttons\']/button[text()=\'Update Activity\']",
                       by_val=By.XPATH)  # ideally shouldn't take very long for this to popup


    print("Clicked on Update")

    # get all the buttons because of issues with xpath locating elements via text
    goto_and_click(driver,"//div[@class=\'jconfirm-buttons\']/button[text()=\'Submit\']",
                            by_val=By.XPATH)

    print("Finished submitting")

    # ensure all close buttons are loaded
    wait_for_viss(driver, "//div[@class=\'jconfirm-buttons\']/button[text()=\'Close\']",
                            by_val=By.XPATH)  # close the confirmation prompt

    # we don't bother manually closing since its far more consistent to just navigate to the next page
    print("Finished: " + link)

# gets first and last index of operand characters
def get_operand_bounds(expression, op_index, is_after):
    # skip over whitespaces before power operator
    operand_end = op_index  # will end on first non-whitespace character

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

    operand_end += shift_dir

    # find the first non whitespace index
    while string.whitespace.__contains__(expression[operand_end]):
        operand_end += shift_dir

    # find the start of the expression
    operand_begin = 0
    if expression[operand_end] == paren_plus:
        curr_index = operand_end
        paren_count = 1  # becomes zero when full parenthesis expression has been closed
        # get to the end of the parenthesis statement
        while paren_count > 0:
            curr_index += shift_dir  # go in shift direction by one character
            curr_char = expression[curr_index]
            if curr_char == paren_plus: paren_count += 1
            if curr_char == paren_minus: paren_count -= 1

        operand_begin = curr_index
    else:
        # find the first space before expression
        if is_after:
            operand_begin = expression.find(' ', __start=op_index + 1) + 1
        else:
            operand_begin = expression.rfind(' ', __end=operand_end) + 1

    return [operand_begin, operand_end]

# converts x^y to pow(x, y)
def update_pow_expr(expression : str):
    # update the format to match what is desired
    pow_index = expression.find('^')
    base_bounds : list[int] = get_operand_bounds(expression, pow_index, False)
    power_bounds = get_operand_bounds(expression, pow_index, True)

    base = expression[base_bounds[0] : base_bounds[1] + 1]
    power = expression[power_bounds[0] : power_bounds[1] + 1]
    operation = "pow(" + base + ", " + power + ")"

    # strip out the power,
    return expression[0 : base[0]] + operation + expression[power_bounds[1] + 1 : len(expression)]

def update_pow_expressions(expression : str):
    # continue to perform replacement on all power expressions until they are replaced
    pow_index = expression.find('^')
    while pow_index > -1:
        expression = update_pow_expr(expression)
        pow_index = expression.find('^')

# will try to replace x^y in drive expressions with pow(x, y) [never in pre or post board]
def replace_drive_pow(driver, link, info):
    # open the link
    driver.get(link)

    # locate each drive in order
        # locate occurrences of x^y
        # update occurrences to desired form

# will try to replace x^y in draw expressions with pow(x, y)
def replace_draw_pow(driver, link, info):
    # open the link
    driver.get(link)

    # iterate through solution, pre, and post board
        # iterate through all draw lines based on expression blocks
            # Update the expression

def get_action(action_name : str):
    if action_name.upper() == "REPLACE_DRIVE_POW":
        return replace_drive_pow
    elif action_name.upper() == "REPLACE_DRAW_POW":
        return replace_draw_pow

    return update_models

def get_action_link(action_name: str):
    return ""

def parse_by_links(action, info, separator):
    driver = init_bare_driver()  # allows images to load properly so they can be selected
    links = []

    # get links from provided link page
    driver.get("https://roboblocky.com/activity-portal/script_linkbotSymbol.php")
    ensure_logged_in(driver)

    link_elements = wait_and_gets(driver, "//a[@target=\'_blank\']", by_val=By.XPATH)
    for element in link_elements:
        links.append(element.get_attribute("href"))

    # used to avoid re-doing previously computed work
    #3244 doesn't have any robots
    start_from_link = "https://roboblocky.com/u/10626.php"
    if start_from_link is not None:
        for i in range(0, len(links)):
            if links[i] == start_from_link:
                links = links[i : len(links)]
                break

    print("All links collected, printing first 20: \n", links[0:20])
    link_index = 0
    for link in links:
        link_index += 1
        print("On link " + str(link_index) + "/" + str(len(links)))
        succeeded = False
        while not succeeded:
            try:
                update_models(driver, link, info)
                succeeded = True
            except Exception as error:
                print("Got error on link: " + link + "<" + str(link_index) + "/" + str(len(links)) + "> of: \n", error)
                print("Trying to run on this link again")
                #update_models(driver, link, info)  # try again
                #print("Navigate to a new webpage to continue process")
                #while driver.current_url == link:
                    #driver.implicitly_wait(5)
            # last line of link processing

    print("Finished processing all links")

def go_to_curriculum(driver, grade_index):
    row = wait_and_gets(driver, "tr", By.TAG_NAME)[int(grade_index / 4)]
    grade = row.find_elements(By.TAG_NAME, "a")[grade_index % 4]
    ActionChains(driver).scroll_to_element(grade).click()

def parse_by_grades(action, info, grades, chapters : list[int] | None):
    driver = init_bare_driver()
    curriculum = "https://roboblocky.com/curriculum/"

    for grade in grades:
        # go to curriculum and ensure we are logged in
        driver.get(curriculum)
        ensure_logged_in(driver)

        # open the current curriculum
        go_to_curriculum(driver, grade + 1)  # we want grade index to start at 0

        chapter_elements = wait_and_gets(driver,
            "//button[@class=\'btn-link text-bold no-padding chapterTitle collapsed\'")

        if chapters is None: chapter = range(0, len(chapter_elements))
        for ch_index in chapters:

            # chapter = wait_and_gets()

            # reset page
            go_to_curriculum(driver, grade + 1)

def parse_args():
    parser = ArgumentParser("AutomaticActivityUpdater")
    parser.add_argument("--action",
                        help="The action you want the updater to perform out of its known list of actions.",
                        type=str,
                        required=False)
    parser.add_argument("--sep",
                        help="If a separator is used, indicate it. Line ends are included.",
                        type=str,
                        required=False)
    parser.add_argument("--info",
                        help="The information to use for the given action (model name, etc).",
                        required=False)
    parser.add_argument("--grades",
                        help="The grade levels to be targeted by the automatic robot searcher.",
                        required=False)
    parser.add_argument("--ch",
                        type=int,
                        help="The specific chapters which are to be targeted. None supplied implies all.",
                        required=False)

    return parser.parse_args()

def activity_updater():
    args = parse_args()
    separator = args.sep
    info = args.info
    action = args.action

    # for now these are just hard set rather than command line
    grades = None # args.grades  -1 -> 16 inclusive range
    chapters = None  # args.ch

    if info is None: info = "LinkbotFace"  # set default model manually

    if action is None: action = "update_models"  # set default action manually

    # ---------------------- START PROCESSING -------------------------- #

    if grades is None: parse_by_links(action, info, separator)
    elif grades is not None:
        parse_by_grades(action, info, grades, chapters)

    # end of updater

if __name__ == '__main__':
    try:
      activity_updater()
    except Exception as e:
        # printl("PrecipitationGrabber execution failed; printing exception: \n" + str(e))
        # printl("Full stack trace \n")
        traceback.print_exc()
