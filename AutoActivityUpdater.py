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
        print("Current login issue: ", error)
        return False

    return True

def activity_updater():
    parser = ArgumentParser("AutomaticActivityUpdater")
    parser.add_argument("--file",
        help="A text file absolute path argument is expected. If this isn't provided, <exec>/data/links.txt/csv is used.",
        type=str,
        required=False)
    parser.add_argument("--separator",
        help="If a separator is used, indicate it. Line ends are included.",
        type=str,
        required=False)
    parser.add_argument("--model_name",
        help="The name of the model to be used (ensure proper capitalization).",
        required=False)
    args = parser.parse_args()
    location = args.file
    separator = args.separator
    model = args.model_name

    # if the supplied location is invalid, we will use the default
    if location is None or not os.path.exists(location):
        location = append_cur_dir("Data", "links.txt")

        # try to get .csv file
        if not os.path.exists(location):
            location = append_cur_dir("Data", "links.csv")
            separator = ","
            if not os.path.exists(location): return

    if model is None: model = "LinkbotFace"

    links : list[str] = []

    # get all the links as strings
    with open(location) as source:
        for line in source:
            if separator is None:
                links.append(line.strip())
                continue
            prev_sep_end = 0  # index at which we consider characters valid again (inclusive)
            next_sep = line.find(separator)
            while next_sep >= 0:
                links.append(line[prev_sep_end : next_sep])
                prev_sep_end = next_sep + len(separator)
                next_sep = line.find(separator, __start=prev_sep_end)

            # process last link with end line separator
            if prev_sep_end < len(separator):
                links.append(line[prev_sep_end : len(separator)])

    print("All links collected: \n", links)
    driver = initialize_driver()

    for link in links:
        print("Beginning processing of: " + link)
        driver.get(link)
        while not is_logged_in(driver):
            print("Waiting for user to login...")
            sleep(7.5)

        # user should be logged in now
        robot_button = wait_for_vis(driver, "robotCollapseButton", by_val=By.ID)
        robot_button.click()

        robots = wait_and_get_vis_vals(driver, "//li[@class=\'robotItem relative \']", by_val=By.XPATH)
        print(robots)
        for index in range(0, len(robots)):
            print("Beginning on robot " + str(index + 1))
            robot = robots[index]

            # attempt to bypass opening model menu and associated issues of clickable image not loading
            image = robot.find_element(by=By.CSS_SELECTOR, value="img")  # select this robot
            model_path = "/img/models/" + model + ".png"
            driver.execute_script("arguments[0].setAttribute(\"src\", \"" + model_path + "\")", image)
            sleep(15)

            #wait_for_vis(driver, "robotModel" + str(index + 1), by_val=By.ID).click()  # open model selection
            #image = wait_and_get(driver, "//img[@value=\'" + model + "\']", 10, by_val=By.XPATH)  # select model
            #wait_for_vis(driver, "closeButton", by_val=By.ID).click()  # close the menu
            print("Finished robot " + str(index + 1))

            # last line of robot processing
        print("Finished processing all robots; preparing to save.")
        robot_button.click()  # close the robot menu
        wait_for_vis(driver, "saveTab", by_val=By.ID).click()  # open the save menu
          # save the activity - requires editor

        print("Finished: " + link)
        # last line of link processing

    print("Finished processing all links")
    # last line of updater



if __name__ == '__main__':
    try:
      activity_updater()
    except Exception as e:
        # printl("PrecipitationGrabber execution failed; printing exception: \n" + str(e))
        # printl("Full stack trace \n")
        traceback.print_exc()
