import selenium
import os
import selenium.webdriver

from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def wait_for_vis(driver, target_id, timeout=10, by_val=By.CSS_SELECTOR):
    wait = WebDriverWait(driver, timeout)
    ret = wait.until(EC.visibility_of_element_located((by_val, target_id)))
    return ret

def wait_and_get(driver, target_id, timeout=10, by_val=By.ID):
    wait = WebDriverWait(driver, timeout)
    return wait.until(EC.presence_of_element_located( (by_val, target_id) ))

def wait_and_get_vis_vals(driver, target_id, timeout=10, by_val=By.ID):
    wait = WebDriverWait(driver, timeout)
    return wait.until(EC.visibility_of_all_elements_located( (by_val, target_id) ))

def make_selection(driver, list_name, visible_choice):
    select = Select(wait_and_get(driver, list_name))

    # wait for option to be present or timeout
    wait = WebDriverWait(driver, 10)
    is_choice_present = lambda d : is_option_present(select, visible_choice)
    wait.until(is_choice_present)

    select.select_by_visible_text(visible_choice)

def is_option_present(select : Select, visible_choice):
    for element in select.options:
        if element.text == visible_choice:
            return True

def is_downloading(driver):
    top_download : WebElement = get_top_download(driver)
    curr_down_desc : list[WebElement] = top_download.shadow_root.find_elements(By.CSS_SELECTOR, "div[class='description']")
    for element in curr_down_desc:
        if element.is_displayed():
            return True

    return False

def get_curr_dir():
    return os.path.dirname(os.path.realpath(__file__))

def append_cur_dir(*suffix : str):
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), *suffix)

# spread out for debugging purposes; assumes driver is on chrome downloads url already
def get_top_download(driver):
    curr_down : WebElement = wait_and_get(driver, "//downloads-manager", by_val=By.XPATH)
    curr_down = curr_down.shadow_root.find_element(value="downloadsList") # does find shadow root
    curr_down = curr_down.find_element(value="list")
    curr_down = curr_down.find_element(value="frb0")
    return curr_down

def initialize_driver(down_dir=append_cur_dir("Downloads")):
    # ensure files downloaded to correct location
    options = selenium.webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-setuid-sandbox")

    options.add_argument("--remote-debugging-port=9222")  # this

    options.add_argument("--disable-dev-shm-using")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("start-maximized")
    options.add_argument("disable-infobars")
    options.add_argument(r"user-data-dir=.\cookies\\test")

    # second pref stops images from loading
    prefs = {"download.default_directory": down_dir}  #, "profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)

    # start driver
    return selenium.webdriver.Chrome(options=options)