from math import ceil

from selenium.webdriver import ActionChains

from SeleniumUtils import *
from time import sleep

# returns the name of the board, or None if neither board is open
def determine_board_type(driver : WebDriver):
    # has style attribute: style="prop1:state; ...; visibility:hidden" if not opened
    is_pre_vis = wait_and_get(driver, "preBoard", By.ID).get_attribute("style").find("hidden") == -1
    if is_pre_vis: return "preBoard"

    is_post_vis = wait_and_get(driver, "postBoard", By.ID).get_attribute("style").find("hidden") == -1
    if is_post_vis: return "postBoard"

    return None

def open_board(driver : WebDriver, is_preboard : bool):
    board_name = get_board_id(is_preboard)
    goto_and_click(driver, "editBoard", By.ID)
    sleep(0.5)  # let the window actually pop up
    goto_and_click(driver, board_name, By.NAME)

def close_board(driver : WebDriver, is_preboard : bool):
    close_id = ""
    if is_preboard:
        close_id = "closePreBoard"
    else:
        close_id = "closePostBoard"

    goto_and_click(driver, close_id, By.ID)

# returns the xpath id for any descendant of the type of board supplied
def board_descendant_prefix(board_type : str):
    return "//div[@id='" + board_type + "']/descendant::"

# returns list containing vertical and horizontal scroll range, respectively
def get_scrolls(driver):
    # we may need to get different scrolls wheels depending on the board open
    board_type = determine_board_type(driver)
    ancestor_string = "//"
    if board_type is not None:
        ancestor_string = board_descendant_prefix(board_type)

    # ensure access to vert scroll
    vert_scroll = wait_and_get(driver, ancestor_string + "*[name()='g' and @class='blocklyScrollbarVertical']",
                                       By.XPATH)

    # ensure access to horizontal scroll
    hori_scroll = wait_and_get(driver, ancestor_string + "*[name()='g' and @class='blocklyScrollbarHorizontal']",
                                       By.XPATH)

    return [vert_scroll, hori_scroll]

# returns a list containing the vertical and horizontal scroll handles, respectively
def get_scroll_handles(driver, scrolls: list[WebElement] | None = None):
    if scrolls is None: scrolls = get_scrolls(driver)

    vert_scroll = scrolls[0]
    hori_scroll = scrolls[1]

    vert_handle = vert_scroll.find_element(By.XPATH, "./*[name()='rect' and @class='blocklyScrollbarHandle']")
    hori_handle = hori_scroll.find_element(By.XPATH, "./*[name()='rect' and @class='blocklyScrollbarHandle']")

    return [vert_handle, hori_handle]

def get_y_trans(element : WebElement):
    element_transform = element.get_attribute("transform")
    return float(element_transform[element_transform.find(',') + 1: element_transform.find(')')])

def get_x_trans(element : WebElement):
    element_transform = element.get_attribute("transform")
    return float(element_transform[element_transform.find('(') + 1 : element_transform.find(',')])

# controls the navigation of the blockly workspace
# works off of the link currently open in the driver
class BlocklyWorkspace:
    def characterize_workspace(self, driver):
        # ensure access to vert scroll
        scrolls = get_scrolls(driver)
        vert_scroll = scrolls[0]
        hori_scroll = scrolls[1]

        handles = get_scroll_handles(driver, scrolls)
        vert_handle = handles[0]
        hori_handle = handles[1]

        ensure_in_view(driver, vert_handle)
        ensure_in_view(driver, hori_handle)

        y_top = vert_scroll.location["y"]
        x_left = hori_scroll.location["x"]
        y_bot = hori_scroll.location["y"] # y_top + vert_scroll.size["height"]
        x_right = vert_scroll.location["x"] # x_left + hori_scroll.size["width"]

        # scroll to edges for both bars
        # negative offset is up for y, left for x
        y_offset = y_bot - (float(vert_handle.get_attribute("y")) + y_top + ceil(vert_handle.rect["height"] / 2))
        x_offset = x_right - (float(hori_handle.get_attribute("x")) + x_left + ceil(hori_handle.rect["width"] / 2))
        ActionChains(driver).click_and_hold(vert_handle).move_by_offset(0, y_offset).release().perform()
        ActionChains(driver).click_and_hold(hori_handle).move_by_offset(x_offset, 0).release().perform()

        # record the max values
        self.y_max = float(vert_handle.get_attribute("y"))
        self.x_max = float(hori_handle.get_attribute("x"))

        canvas = wait_and_get(driver, "//*[name()='g' and @class='blocklyBlockCanvas']", By.XPATH)
        self.canvasTL_edge_y: float = get_y_trans(canvas)
        self.canvasTL_edge_x: float = get_x_trans(canvas)

        # reset back to 0, 0
        ActionChains(driver).click_and_hold(vert_handle).move_by_offset(0, -int(self.y_max)).release().perform()
        ActionChains(driver).click_and_hold(hori_handle).move_by_offset(-int(self.x_max), 0).release().perform()

        self.canvasTL_origin_y: float = get_y_trans(canvas)
        self.canvasTL_origin_x: float = get_x_trans(canvas)

        canvas_y_range: float = self.canvasTL_origin_y - self.canvasTL_edge_y
        canvas_x_range: float = self.canvasTL_origin_x - self.canvasTL_edge_x

        self.scroll_per_height = self.y_max / canvas_y_range  # canvas.rect["height"]
        self.scroll_per_width = self.x_max / canvas_x_range  # canvas.rect["width"]

    def __init__(self, driver):
        self.y_max: float = 0
        self.x_max: float = 0
        self.canvasTL_origin_y: float = 0
        self.canvasTL_origin_x : float = 0
        self.canvasTL_edge_y: float = 0
        self.canvasTL_edge_x : float = 0
        self.scroll_per_height: float = 0
        self.scroll_per_width : float = 0
        self.characterize_workspace(driver)

    def scroll_to(self, driver : WebDriver, element : WebElement):
        y_shift = 0
        x_shift = 0

        # go past all non blocklyDraggable parents
        parent = element
        while parent.get_attribute("class") != "blocklyDraggable":
            # try to add the translation if present
            if parent.get_attribute("transform") is not None:
                y_shift += get_y_trans(parent)
                x_shift += get_x_trans(parent)
            parent = parent.find_element(By.XPATH, "./..")

        # start collecting translation data
        y_shift += get_y_trans(parent)
        x_shift += get_x_trans(parent)

        # determine total shift
        # collect shifts from all draggable parents (stops at canvas level)
        parent = parent.find_element(By.XPATH, "./..")
        while parent.get_attribute("class") == "blocklyDraggable":
            y_shift += get_y_trans(parent)
            x_shift += get_x_trans(parent)
            parent = parent.find_element(By.XPATH, "./..")

        # the scroll bar elements store information
        scrolls = get_scrolls(driver)
        vert_scroll = scrolls[0]
        hori_scroll = scrolls[1]

        # the handles are used for interaction
        handles = get_scroll_handles(driver, scrolls)
        vert_handle = handles[0]
        hori_handle = handles[1]

        ensure_in_view(driver, vert_handle)
        ensure_in_view(driver, hori_handle)

        curr_y_offset : float = float(get_y_trans(vert_scroll))
        curr_x_offset : float = float(get_x_trans(hori_scroll))

        y_offset = int(y_shift * self.scroll_per_height - curr_y_offset)
        x_offset = int(x_shift * self.scroll_per_width - curr_x_offset)

        # try to navigate to element
        ActionChains(driver).click_and_hold(vert_handle).move_by_offset(0, y_offset).release().perform()
        ActionChains(driver).click_and_hold(hori_handle).move_by_offset(x_offset,0).release().perform()

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
        sleep(1)
    print("User login detected.")

# downloads activity by opening save tab and then hitting save
def download_activity(driver : WebDriver, board_index : int):
    save_id : str = "saveTab"
    if board_index > 1: save_id += str(board_index)
    goto_and_click(driver, save_id, By.ID)
    goto_and_click(driver, "//div[@class=\'jconfirm-buttons\']/button[text()=\'Save\']", By.XPATH)

# performs the actions necessary to save, but does not clean up save menu (leaves it open)
def save_activity(driver, is_lesson=None, board_index : int=1):
    save_tab_id : str = "saveTab"
    if board_index != 1: save_tab_id += str(board_index)
    goto_and_click(driver, save_tab_id, by_val=By.ID)  # open the save menu

    if is_lesson is None:
        try:
            # we try to quickly cause a throw if this is not a lesson
            wait_and_get(driver, "//div[@class=\'jconfirm-buttons\']/button[contains(text(), \'Update Lesson\')]",
                         by_val=By.XPATH, timeout=1)
            print("This is a lesson")
            goto_and_click(driver, "//div[@class=\'jconfirm-buttons\']/button[contains(text(), \'Update Lesson\')]",
                           by_val=By.XPATH, timeout=5)

        except Exception as error:
            print("This is an activity")
            goto_and_click(driver, "//div[@class=\'jconfirm-buttons\']/button[contains(text(), \'Update Activity\')]",
                           by_val=By.XPATH)  # ideally shouldn't take very long for this to popup
    elif is_lesson:
        goto_and_click(driver, "//div[@class=\'jconfirm-buttons\']/button[contains(text(), \'Update Lesson\')]",
                       by_val=By.XPATH, timeout=5)
    else:
        goto_and_click(driver, "//div[@class=\'jconfirm-buttons\']/button[contains(text(), \'Update Activity\')]",
                       by_val=By.XPATH)  # ideally shouldn't take very long for this to popup

    print("Clicked on Update")

    goto_and_click(driver, "//p[text()[contains(., 'will update')]]/ancestor::*//div[@class=\'jconfirm-buttons\']/button[text()=\'Submit\']",
                   by_val=By.XPATH)

    print("Finished submitting")

    # ensure all close buttons are loaded
    wait_for_vis(driver, "//span[@class='jconfirm-title' and text()='Success']/ancestor::*//div[@class=\'jconfirm-buttons\']/button[text()=\'Close\']",
                  by_val=By.XPATH)  # close the confirmation prompt


def get_robots(driver):
    # user should be logged in now
    robot_tab = wait_for_vis(driver, "robotCollapseButton", by_val=By.ID)
    ActionChains(driver).scroll_to_element(robot_tab)
    if robot_tab.get_attribute("aria-expanded") == "false": robot_tab.click()  # expand if not already

    # in case activity does not have robot (which happens surprisingly more than a few times)
    try:
        wait_and_get(driver, "//li[contains(@class, 'robotItem relative') and not(contains(@class, 'hide'))]",
                     by_val=By.XPATH, timeout=1)
    except Exception as error:
        print("No robots in this activity; skipping")
        return None

    robots = wait_for_viss(driver, "//li[contains(@class, 'robotItem relative') and not(contains(@class, 'hide'))]",
                           by_val=By.XPATH)
    return robots


def select_target_type(driver, is_example, target_num):
    if target_num is not None:
        # select relevant "sub-page"
        if is_example and target_num:
            goto_and_click(driver, "loadExample" + target_num, By.ID)
        else:
            goto_and_click(driver, "loadSolution" + target_num, By.ID)


def open_and_ignore_prompt(driver, link):
    driver.get(link)
    # ensure_logged_in(driver)  # we can generally assume the user is already logged in

    # see if there is a popup prompt we need to get rid of
    try:
        prompt_close = wait_for_vis(driver, "//div[@class=\'jconfirm-buttons\']/button[text()=\'Close\']",
                                    by_val=By.XPATH, timeout=1)
        prompt_close.click()
        print("A prompt was found and ignored")
    except Exception as exception:
        print("No prompt found")
