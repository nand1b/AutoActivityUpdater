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
        wait_and_get(driver, "//a[text()=\'Lesson Plan\']", by_val=By.XPATH, timeout=1)
        print("This is a lesson")
        goto_and_click(driver, "//div[@class=\'jconfirm-buttons\']/button[text()=\'Update Lesson\']",
                       by_val=By.XPATH)

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

def parse_by_links(model, location, separator):
    links : list[str] = parse_out_links(location, separator)

    driver = init_bare_driver()  # allows images to load properly so they can be selected
    if len(links) < 1:
        # get links from provided link page
        driver.get("https://roboblocky.com/activity-portal/script_linkbotSymbol.php")
        ensure_logged_in(driver)

        link_elements = wait_and_gets(driver, "//a[@target=\'_blank\']", by_val=By.XPATH)
        for element in link_elements:
            links.append(element.get_attribute("href"))

    # used to avoid re-doing previously computed work
    #3244 doesn't have any robots
    start_from_link = "https://roboblocky.com/u/3244.php"
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
        try:
            update_models(driver, link, model)
        except Exception as error:
            print("Got error on link: " + link + "<" + str(link_index) + "/" + str(len(links)) + "> of: \n", error)
            print("Trying to run on link one more time")
            update_models(driver, link, model)  # try again
            #print("Navigate to a new webpage to continue process")
            #while driver.current_url == link:
                #driver.implicitly_wait(5)
        # last line of link processing

    print("Finished processing all links")

def go_to_curriculum(driver, grade_index):
    row = wait_and_gets(driver, "tr", By.TAG_NAME)[int(grade_index / 4)]
    grade = row.find_elements(By.TAG_NAME, "a")[grade_index % 4]
    ActionChains(driver).scroll_to_element(grade).click()

def parse_by_grades(model, grades, chapters : list[int] | None):
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

            chapter = wait_and_gets()

            # reset page
            go_to_curriculum(driver, grade + 1)

def parse_args():
    parser = ArgumentParser("AutomaticActivityUpdater")
    parser.add_argument("--file",
                        help="A text file absolute path argument is expected. If this isn't provided, <exec>/data/links.txt/csv is used.",
                        type=str,
                        required=False)
    parser.add_argument("--sep",
                        help="If a separator is used, indicate it. Line ends are included.",
                        type=str,
                        required=False)
    parser.add_argument("--model",
                        help="The name of the model to be used (ensure proper capitalization).",
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
    location = args.file
    separator = args.sep
    model = args.model

    # for now these are just hard set rather than command line
    grades = None # args.grades  -1 -> 16 inclusive range
    chapters = None  # args.ch

    # if the supplied location is invalid, we will use the default
    if location is None or not os.path.exists(location):
        location = append_cur_dir("Data", "links.txt")

        # try to get .csv file
        if not os.path.exists(location):
            location = append_cur_dir("Data", "links.csv")
            separator = ","
            if not os.path.exists(location): return

    if model is None: model = "LinkbotFace"

    # ---------------------- START PROCESSING -------------------------- #

    if grades is None: parse_by_links(model, location, separator)
    elif grades is not None:
        parse_by_grades(model, grades, chapters)

    # end of updater

if __name__ == '__main__':
    try:
      activity_updater()
    except Exception as e:
        # printl("PrecipitationGrabber execution failed; printing exception: \n" + str(e))
        # printl("Full stack trace \n")
        traceback.print_exc()
