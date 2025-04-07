import selenium
import selenium.webdriver

from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from Utils import *

global_timeout = 10  # sometimes pages need a long time to load or for a connection to re-stabilize

def print_element(driver : WebDriver, element : WebElement):
    # print("accessible name: " + element.accessible_name + ", tag: " + element.tag_name + ", text: " + element.text)
    print(driver.execute_script("return \"Outer: \\n\" + arguments[0].outerHTML + \"\\n Inner: \\n\" + arguments[0].innerHTML", element))
    print("\n")

# assumes an element has already been confirmed present
def ensure_in_view(driver, element : WebElement, timeout=global_timeout):
    wait = WebDriverWait(driver, timeout)
    driver.execute_script("arguments[0].scrollIntoView(true)", element)
    # ActionChains(driver).scroll_to_element(element)
    ret = wait.until(EC.visibility_of(element))
    return ret

def goto_and_click(driver, target_id, by_val=By.XPATH, timeout=global_timeout):
    element = wait_and_get(driver, target_id, by_val, timeout)
    # ActionChains(driver).scroll_to_element(element).perform()
    ensure_in_view(driver, element)
    WebDriverWait(driver, global_timeout).until(EC.element_to_be_clickable(element))
    # ensure_in_view(driver, element).click()  # double check this would be in view?
    wait_for_vis(driver, target_id, by_val, timeout).click()  # apparently we need to relocate it to avoid intercepts

def wait_for_vis(driver, target_id, by_val=By.CSS_SELECTOR, timeout=global_timeout):
    wait = WebDriverWait(driver, timeout)
    ret = wait.until(EC.visibility_of_element_located((by_val, target_id)))
    return ret

# will just immediately try to get an element if it exists
def get_if_exists(driver : WebDriver, target_id, by_val=By.XPATH):
    result = None
    try:
        result = driver.find_element(by_val, target_id)
    except Exception as error:
        pass

    return result

def wait_and_get(driver, target_id, by_val=By.CSS_SELECTOR, timeout=global_timeout):
    wait = WebDriverWait(driver, timeout)
    return wait.until(EC.presence_of_element_located( (by_val, target_id) ))

def wait_and_gets(driver, target_id, by_val=By.CSS_SELECTOR, timeout=global_timeout):
    wait = WebDriverWait(driver, timeout)
    return wait.until(EC.presence_of_all_elements_located((by_val, target_id)))

def wait_for_viss(driver, target_id, by_val=By.CSS_SELECTOR, timeout=global_timeout):
    wait = WebDriverWait(driver, timeout)
    return wait.until(EC.visibility_of_all_elements_located( (by_val, target_id) ))

def make_selection(driver, list_name, visible_choice):
    select = Select(wait_and_get(driver, list_name))

    # wait for option to be present or timeout
    wait = WebDriverWait(driver, global_timeout)
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

# spread out for debugging purposes; assumes driver is on chrome downloads url already
def get_top_download(driver):
    curr_down : WebElement = wait_and_get(driver, "//downloads-manager", by_val=By.XPATH)
    curr_down = curr_down.shadow_root.find_element(value="downloadsList") # does find shadow root
    curr_down = curr_down.find_element(value="list")
    curr_down = curr_down.find_element(value="frb0")
    return curr_down

def init_bare_driver():
    options = selenium.webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")  # apparently this is very insecure, but it should be okay
    options.add_argument("disable-infobars")
    options.add_argument(r"user-data-dir=" + str(append_cur_dir("cookies", "testing0")))
    return selenium.webdriver.Chrome(options=options)  # program may get stuck here if it can't get enough resources

def initialize_driver(down_dir=append_cur_dir("Downloads")):
    # ensure files downloaded to correct location
    # this will likely cause images to load incorrectly
    options = selenium.webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-setuid-sandbox")

    options.add_argument("--remote-debugging-port=9222")

    options.add_argument("--disable-dev-shm-using")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("start-maximized")
    options.add_argument("disable-infobars")
    options.add_argument(r"user-data-dir=.\cookies\\test")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36")

    # second pref stops images from loading
    prefs = {"download.default_directory": down_dir}  #, "profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)

    # start driver
    return selenium.webdriver.Chrome(options=options)