import traceback
from argparse import ArgumentParser

from selenium.webdriver import Keys

from DriverUtils import *

import pyautogui

# updates the model without closing the robot menu
def update_model(driver, robot : WebElement, index : int, model):
    robot_button = robot.find_element(By.TAG_NAME, "button")
    robot_button.click()

    wait_for_vis(driver, "robotModel" + str(index + 1), by_val=By.ID).click()  # open model selection
    goto_and_click(driver, "//img[@value=\'" + model + "\']", By.XPATH)  # select model
    wait_for_vis(driver, "closeButton", by_val=By.ID).click()  # close the menu

def try_fixup(driver : WebDriver, link, is_lesson, model):
    robots = get_robots(driver)
    if robots is None or len(robots) < 1: return

    models = []
    for robot in robots:
        robot_button = robot.find_element(By.TAG_NAME, "button")
        robot_model = robot_button.find_element(By.TAG_NAME, "img").get_attribute("src")
        models.append(robot_model[34 : len(robot_model) - 4])  # exclude .png from model name

    error_filename = "PotentialOverwrites.txt"

    source = get_if_exists(driver, "//button[contains(@id, 'loadExample') and not(contains(@class, 'active'))]", By.XPATH)
    if source is None:
        source = get_if_exists(driver, "//button[contains(@id, 'loadSolution') and not(contains(@class, 'active'))]", By.XPATH)

    if source is None:
        print("No source found for fixup; ending fixup attempt.")
        write_to_file(error_filename, "NO SOURCE: " + link + "\n")
        return

    ensure_in_view(driver, source)
    source.click()
    robots = get_robots(driver)
    if robots is None or len(robots) < 1: return

    if len(robots) != len(models):
        print("Model count mismatch between target and source; ending fixup attempt.")
        write_to_file(error_filename, "MODEL COUNT MISMATCH: " + link + " - " + driver.title + "\n")
        return

    source_models = []
    for robot in robots:
        robot_button = robot.find_element(By.TAG_NAME, "button")
        robot_model = robot_button.find_element(By.TAG_NAME, "img").get_attribute("src")
        source_models.append(robot_model[34: len(robot_model) - 4])

    print("Found original models: " + str(models) + " and source models: " + str(source_models))

    has_non_linkbot = False
    for source_model in source_models:
        if source_model != "Linkbot" and source_model != "LinkbotFace":
            has_non_linkbot = True
            break

    if not has_non_linkbot:
        print("No fix is needed in fixup attempt.")
        write_to_file(error_filename, "NO FIX APPLIED: " + link + " - " + driver.title + "\n")
        return

    print("A fix will be applied in the current fixup attempt.")
    write_to_file(error_filename, "APPLIED FIX(es): " + link + " - " + driver.title + "\n")

    open_and_ignore_prompt(driver, link)  # go back to original start blocks
    robots = get_robots(driver)
    for i in range(0, len(models)):
        if source_models[i] == "Linkbot": continue  # these models should have been changed
        if model[i] == source_models[i]: continue  # agreement means this was done correctly
        update_model(driver, robots[i], i, source_models[i])

    wait_for_vis(driver, "robotCollapseButton", by_val=By.ID).click()  # close menu
    save_activity(driver, is_lesson)

    return  # we do not need to redo start blocks

def update_models(driver, link, info : list[str]):
    print("Beginning processing of: " + link)
    model = info[len(info) - 1]  # last info is always model
    link_info : LinkInfo = LinkInfo(info[0])

    # open the link
    open_and_ignore_prompt(driver, link)

    # extract info
    is_lesson = link_info.is_lesson()  # if this is lesson or activity
    is_example = link_info.is_example()  # if this is example or solution/start blocks
    target_num = link_info.get_num_str()  # if this is start blocks (None) or what number to target

    print("Trying fixup")

    # try to fix start blocks, since we have iterated over all of them already
    try_fixup(driver, link, is_lesson, model)  # try to fix all the start blocks

    print("Finished trying fixup")
    print("Beginning with is_example: " + str(is_example) + ", target_num: " + str(target_num))

    open_and_ignore_prompt(driver, link)  # we need to reset page after fixup attempt

    select_target_type(driver, is_example, target_num)  # opens example or solution of correct num if relevant

    robots = get_robots(driver)
    if robots is None: return

    # set the models
    for index in range(0, len(robots)):
        print("Beginning on robot " + str(index + 1) + "/" + str(len(robots)))
        robot = robots[index]  # they should be in order

        robot_model = robot.find_element(By.TAG_NAME, "button").find_element(By.TAG_NAME, "img").get_attribute("src")
        if robot_model[34 : len(robot_model) - 4] != "Linkbot": continue  # don't update non linkbot models

        update_model(driver, robot, index, model)
        print("Finished robot " + str(index + 1))

        # last line of robot processing

    # close the robot menu
    print("Finished processing all robots; preparing to save.")
    wait_for_vis(driver, "robotCollapseButton", by_val=By.ID).click()  # perform close

    # save changes
    save_activity(driver, is_lesson)

    # we don't bother manually closing since its far more consistent to just navigate to the next page
    print("Finished: " + link)

def is_draw_replace(expression : str) -> bool:
    return expression == "draw_expr"

def replace_pow_xml(driver : WebDriver, link , info : list[str]):
    # open the link
    open_and_ignore_prompt(driver, link)

    target_expression: str = info[len(info) - 1]
    is_draw : bool = is_draw_replace(target_expression)
    target_name = "expr"
    if is_draw: target_name = "VALUE_4"

    link_info: LinkInfo = LinkInfo(info[0])
    is_lesson = link_info.is_lesson()
    is_example = link_info.is_example()
    target_num = link_info.get_num_str()
    has_board = link_info.is_pre() or link_info.is_post()  # neither board should be on for start blocks

    select_target_type(driver, is_example, target_num)  # open example or solution

    # will open the correct board, or none of that is appropriate
    board_type = None
    board_index : int = 1
    if has_board:
        if link_info.is_pre():
            board_type = "PreBoard"
            board_index = 2
        else:
            board_type = "PostBoard"
            board_index = 3
        open_board(driver, link_info.is_pre())

    title = driver.title

    # download the activity and get details about the downloaded file
    download_activity(driver, board_index)
    file_name = get_top_download(driver).shadow_root.find_element(By.ID, "name").get_attribute("title")
    file_location = append_cur_dir("Downloads", file_name)

    # begin parsing the activity with a log file open to write info to
    with open(append_cur_dir("Logging", "xml_log.txt"), 'a') as log:
        log.write("Opening: " + file_name + " - " + title + "; " + info[0] + "\n")
        print("\nOpening: " + file_name + " - " + title + "; " + info[0] + "\n")
        curr_link_xml = etree.parse(file_location, etree.XMLParser(remove_blank_text=True))

        # because of the complications with namespaces with lxml and the fact that only one is ever used,
        # I am just using the * and local name to avoid the headache and poor documentation
        # apparently elements come out as [<Element {http://www.w3.org/1999/xhtml}block at 0x7fd7f814e440>]
        # apparently using .// isn't allowed
        key = "//*[local-name()='block' and contains(@type, '" + target_expression + "')]//*[local-name()='value' and @name='" + target_name + "']"
        expressions = curr_link_xml.xpath(key)
        did_update = False
        for expression in expressions:
            container = expression[0]
            # pure text has simpler handling
            if container.attrib["type"] == "text":
                print("Inspecting " + container[0].text + "\n")
                updated_text = update_pow_expressions(container[0].text)
                if updated_text != container[0].text:
                    did_update = True
                    container[0].text = updated_text
                    print("Updated to " + updated_text + "\n")
                continue

            # if the expression isn't pure text or a text combination we can't modify it
            if container.attrib["type"] != "text_join":
                log.write("\t Found non-text/text-join element matching expression!\n")
                continue

            expr_updated = update_expression_container(container)
            if not did_update: did_update = expr_updated

        if not did_update:
            log.write("\t ------- No update needed ------- \n")
            print("No update needed for preceding activity. \n")
            return  # nothing needed to be changed so we can skip
        curr_link_xml.write(append_cur_dir("Results", file_name), pretty_print=True)
        log.write("Finished: " + file_name + " - " + title + "; " + info[0] + "\n")
        print("Finished: " + file_name + " - " + title + "; " + info[0] + "\n")

    path_components = append_cur_dir("Results", file_name)
    path_components = path_components[path_components.find("PycharmProjects") : len(path_components)].split(os.sep)

    # go back to activity and load the new xml file
    open_and_ignore_prompt(driver, link)
    select_target_type(driver, is_example, target_num)
    if has_board: open_board(driver, link_info.is_pre())

    # results in either loadBlocks or loadPreBoard or loadPostBoard
    load_id = "load"
    if has_board: load_id += board_type
    else: load_id += "Blocks"
    goto_and_click(driver, load_id, By.ID)

    # results in either loadBlocksMachine or loadBoardMachine
    load_id = "load"
    if has_board: load_id += "Board"
    else: load_id += "Blocks"
    load_id += "Machine"
    load_button = wait_for_vis(driver, load_id, By.NAME)

    # ensure browser is in focus, even though it should always be "on top". Assumes browser farthest right and
    # assumes the browser is reasonably wide
    browser_top_x : int = pyautogui.size()[0] * 3 / 4  # guessing the top is roughly 3/4 of the screen
    browser_top_y : int = 15  # around 15 pixels from the top of the screen
    prev_x : int = pyautogui.position()[0]
    prev_y : int = pyautogui.position()[1]

    # focus browser and hold
    pyautogui.mouseDown(browser_top_x, browser_top_y, button='left')
    pyautogui.sleep(0.2)
    pyautogui.mouseUp(button='left')
    sleep(0.2)  # let the browser realize we don't want to drag it

    pyautogui.moveTo(prev_x, prev_y)  # return to previous position
    load_button.click()  # must be in focus to open

    # must be in focus to work
    for file in path_components:
        sleep(0.5)  # ensure after enter is hit the explorer has time to respond, or when it first opens
        pyautogui.hotkey('ctrl', 'f')
        pyautogui.write(file, 0.005)
        sleep(0.2)  # enforce a manual delay to stop ctrl f and enter being pressed too close together
        pyautogui.press('enter')

    sleep(0.25)  # let the browser respond to the upload
    goto_and_click(driver, "//button[text()='Replace existing blocks']")

    # we do not need to save changes to activity if we just changed board- only save part you changed
    save_activity(driver, is_lesson, board_index)
    sleep(0.5)  # give saving some time just in case

    print("Finished saving current link.")


# will try to replace x^y in drive expressions with pow(x, y) [never in pre or post board]
def replace_pow_interactive(driver : WebDriver, link, info : list[str]):
    # open the link
    open_and_ignore_prompt(driver, link)

    target_expression : str = info[len(info) - 1]

    link_info : LinkInfo = LinkInfo(info[0])
    is_lesson = link_info.is_lesson()
    is_example = link_info.is_example()
    target_num = link_info.get_num_str()
    has_board = link_info.is_pre() or link_info.is_post()  # neither board should be on for start blocks

    select_target_type(driver, is_example, target_num)
    svg_lineage = "//"
    if has_board:
        open_board(driver, link_info.is_pre())
        svg_lineage = board_descendant_prefix(get_board_id(link_info.is_pre()))

    # apparently svg elements must be captured directly, not as children of other elements ?
    svgs = wait_and_gets(driver, svg_lineage + "*[name()='svg' and @class='blocklySvg']", By.XPATH)
    workspace_svg = None
    for svg in svgs:
        if svg.find_element(By.XPATH, "./..").get_attribute("id") == "content_blocks":
            workspace_svg = svg
            break

    # for some reason, this xpath formulation of contains is necessary. Not sure why
    targeted_texts = workspace_svg.find_elements(By.XPATH, "./descendant::*[text()[contains(., '" + target_expression + "')]]")
    for curr_text in targeted_texts:
        #print_element(driver, curr_carrier)

        # we use contains so that even selected elements are considered
        parent = curr_text.find_element(By.XPATH, "./..")
        sub_blocks = parent.find_elements(By.XPATH, "./child::*[name()='g' and @class='blocklyDraggable']")
        # expression_block = sub_blocks[len(sub_blocks) - 2]  # last draggable is next draggable, second to last is expr
        sub_blocks.sort(key=lambda sub_block: get_x_trans(sub_block))  # our target should be furthest right (>> x trans)
        expression_block = sub_blocks[len(sub_blocks) - 1]
        text_boxes = expression_block.find_elements(By.XPATH, "./child::*[name()='g' and @class='blocklyEditableText']")

        for text_box in text_boxes:
            text_element = text_box.find_element(By.XPATH, "./child::*[name()='text' and @class='blocklyText']")

            workspace : BlocklyWorkspace = BlocklyWorkspace(driver)
            workspace.scroll_to(driver, text_element)

            # update the expression
            updated_text = update_pow_expressions(text_element.text)
            if updated_text == text_element.text: continue
            ActionChains(driver).move_to_element(text_element).click().perform()  # go to element and select it
            ActionChains(driver).send_keys(Keys.BACKSPACE).perform()  # acts as if a keystroke was pressed
            ActionChains(driver).send_keys_to_element(text_box, updated_text).perform()  # directly sends keys

            # de-select the block
            ActionChains(driver).move_to_element(parent).move_by_offset(1 + parent.size["width"] / 2, 0).click().perform()

    # we need to close the board before we save this link
    if has_board: close_board(driver, link_info.is_pre())

    save_activity(driver, is_lesson)

    print("Finished replacing drive power expressions for: " + link)

def get_action(action_name : str):
    if action_name.upper() == "REPLACE_POW":
        return replace_pow_interactive
    elif action_name.upper() == "REPLACE_POW_XML":
        return replace_pow_xml

    return update_models

def parse_by_links(action, target_info, separator):
    driver = init_bare_driver()  # allows images to load properly so they can be selected
    links = []
    info : list[list[str]] = []

    # get links from provided link page
    source_link : str = "https://www.roboblocky.com/activity-portal/script_drawExprPower.php"
    start_from_link = None # "https://www.roboblocky.com/u/8407.php"
    driver.get(source_link)  # useful even if we don't parse from it because we want to make sure user is logged in

    # store the link list
    last_split_index: int = source_link.rfind('/')
    link_file_dir = append_cur_dir("Logging", source_link[last_split_index + 1: len(source_link) - 4] + ".txt")
    if os.path.exists(link_file_dir):
        # read from link file
        with open(link_file_dir, 'r') as link_file:
            lines = link_file.readlines()
            line_count : int = 0
            while line_count < len(lines):
                link_line = lines[line_count]
                info_line = lines[line_count + 1]
                links.append(link_line[link_line.find("]:") + 3 : len(link_line) - 1])  # ensure to drop \n
                info.append([info_line[info_line.find('[') + 1 : info_line.rfind(']')].strip('\'')])  # drop '

                # skip the whitespace line
                line_count += 3
    else:
        # parse from list of links
        print("Gathering links...")
        link_elements = wait_and_gets(driver, "//div[@class='row']//a[@target=\'_blank\']", by_val=By.XPATH)
        for element in link_elements:
            links.append(element.get_attribute("href"))
            info.append([element.text.strip('\'')])  # we will parse this later

        # write to file
        with open(link_file_dir, 'a') as link_file:
            for i in range(0, len(links)):
                link_file.write("[" + str(i) + "]: " + links[i] + "\n    INFO: " + str(info[i]) + "\n\n")

    print("Finished gathering links, pruning now.")

    # used to avoid re-doing previously computed work
    if start_from_link is not None:
        for i in range(0, len(links)):
            if links[i] == start_from_link:
                links = links[i : len(links)]
                info = info[i : len(info)]
                break

    # the list automatically shrinks when its been detected as completed?
    print("Finished pruning, beginning looping.")
    ensure_logged_in(driver)

    #links = ["https://roboblocky.com/u/5932.php"]
    action = get_action(action)
    #print("All links collected, printing first 20: \n", links[0:20])
    link_index = 0
    for i in range(0, len(links)):
        link = links[i]
        curr_info = info[i]
        curr_info.append(target_info)  # last piece of information is always model
        link_index += 1
        print("On link " + str(link_index) + "/" + str(len(links)) + " with info: " + str(curr_info))
        succeeded = False
        while not succeeded:
            try:
                action(driver, link, curr_info)
                succeeded = True
            except Exception as error:
                print("Got error on link: " + link + "<" + str(link_index) + "/" + str(len(links)) + ">  of: \n", error,
                      "\n and traceback: \n", traceback.format_exc())
                print("Trying to run on this link again")
                #update_models(driver, link, info)  # try again
                #print("Navigate to a new webpage to continue process")
                #while driver.current_url == link:
                    #driver.implicitly_wait(5)
            # last line of link processing

    print("Finished processing all links")
    driver.quit()

def go_to_curriculum(driver, grade_index):
    row = wait_and_gets(driver, "tr", By.TAG_NAME)[int(grade_index / 4)]
    grade = row.find_elements(By.TAG_NAME, "a")[grade_index % 4]
    ActionChains(driver).scroll_to_element(grade).click()

def parse_by_grades(action, info, grades : list[int] | None, chapters : list[int] | None):
    if grades is None:
        print("No grades supplied; returning.")
        return

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

    driver.quit()

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

def do_test() -> bool:
    return False
    print(inspect_pow_expressions("0.50*pow((2,x))"))
    return True

def activity_updater():
    args = parse_args()
    separator = args.sep
    info = args.info
    action = args.action

    if do_test(): return  # only do test

    # for now these are just hard set rather than command line
    grades = None # args.grades  -1 -> 16 inclusive range
    chapters = None  # args.ch

    if info is None: info = "draw_expr"  # manually set info

    if action is None: action = "replace_pow_xml"  # set default action manually

    if not os.path.exists(append_cur_dir("Logging")): os.mkdir(append_cur_dir("Logging"))
    if not os.path.exists(append_cur_dir("Results")): os.mkdir(append_cur_dir("Results"))

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
