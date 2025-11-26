import os
import time
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class CargomaticAgent:
    def __init__(self, headless=True):
        self.headless = headless
        self.browser = None
        self.page = None
        self.playwright = None
        self.base_url = "https://command-staging.cargomatic.com"

    def start(self):
        """Starts the browser session."""
        self.playwright = sync_playwright().start()
        # Use a persistent context to save login state (cookies, etc.)
        user_data_dir = os.path.join(os.getcwd(), "chrome_user_data")
        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir,
            headless=False,
            viewport={"width": 1280, "height": 720},
            args=["--start-maximized"] # Optional: start maximized
        )
        # If there are no pages open, create a new one. Otherwise, use the first existing page.
        if not self.context.pages:
            self.page = self.context.new_page()
        else:
            self.page = self.context.pages[0]
        self.page.set_default_timeout(15000)
        print("Browser started with persistent context.")

    def login(self, username, password):
        """Logs into the Cargomatic Command Center."""
        print(f"Navigating to {self.base_url}...")
        try:
            self.page.goto(self.base_url)
            
            # Check if we are already logged in or redirected to login
            if "login" in self.page.url:
                print("Logging in...")
                # Wait for login form
                self.page.wait_for_selector("#login-username")
                
                # Fill credentials
                self.page.fill("#login-username", username)
                self.page.fill("#login-password", password)
                
                # Click login
                self.page.click("#login-submit-button")
                
                # Wait for navigation to dashboard or shipments
                # The URL should change from /login
                self.page.wait_for_function("window.location.href.indexOf('login') === -1")
                print(f"Login successful! Current URL: {self.page.url}")
            else:
                print("Already logged in or redirected.")
                
        except Exception as e:
            print(f"Login failed: {e}")
            # Take screenshot for debugging
            self.page.screenshot(path="login_debug.png")
            print("Screenshot saved to login_debug.png")
            # Dump HTML
            with open("login_debug.html", "w") as f:
                f.write(self.page.content())
            print("Dumped login page HTML to login_debug.html")

    def search_shipment(self, reference_number):
        """Searches for a shipment by Reference Number."""
        print(f"Searching for shipment: {reference_number}")
        
        # Ensure we are on the shipments page
        if "shipments" not in self.page.url:
            self.page.goto(f"{self.base_url}/shipments")
        
        # Wait for the reference input
        ref_input_selector = "input[placeholder='Enter a reference number (Ex: 123456)']"
        
        try:
            self.page.wait_for_selector(ref_input_selector, timeout=5000)
            self.page.fill(ref_input_selector, reference_number)
            
            # Click Apply. 
            apply_button_selector = "button.button-hollow-green:has-text('Apply')"
            self.page.click(apply_button_selector)
            
            time.sleep(3) # Wait for results
            
        except Exception as e:
            print(f"Search failed: {e}")

    def search_global(self, reference_number):
        """Searches for a shipment using the global search bar."""
        print(f"Searching globally for: {reference_number}")
        try:
            # Wait for the global search input
            # Based on previous research, it might be an input with placeholder "Search for any reference #..."
            global_search_selector = "input[placeholder='Search for any reference #...']"
            self.page.wait_for_selector(global_search_selector)
            
            self.page.fill(global_search_selector, reference_number)
            self.page.press(global_search_selector, "Enter")
            
            print("Search submitted. Waiting for results...")
            # Wait for dropdown
            result_selector = "a.list-group-item"
            self.page.wait_for_selector(result_selector, timeout=10000)
            
            print("Clicking first result...")
            self.page.click(result_selector)
            
            # Wait for navigation to details page
            print("Waiting for navigation to shipment details...")
            self.page.wait_for_url("**/shipments/**", timeout=20000)
            print(f"Navigated to: {self.page.url}")
            
            # Extract shipment info (Pickup/Delivery)
            self.extract_shipment_info()
            
            # Navigate to Shipper Profile
            self.click_shipper_link()
            
            # Navigate to SOP and find rate card
            self.navigate_to_sop()
            self.find_rate_card()
                
        except Exception as e:
            print(f"Global search failed: {e}")

    def get_shipper_info(self):
        """Extracts shipper information from the details page."""
        print("Extracting Shipper Information...")
        try:
            # Wait for loading to finish
            print("Waiting for page content to load...")
            try:
                self.page.wait_for_selector("text=Loading...", state="detached", timeout=10000)
            except:
                print("Warning: 'Loading...' did not detach or wasn't found.")
            
            # Wait a bit more for render
            time.sleep(2)

            # Locate the Shipper section
            # Structure: dt with "Shipper" -> sibling dd -> div -> div -> a -> strong
            shipper_header = self.page.locator("dt:has-text('Shipper')")
            if shipper_header.count() > 0:
                shipper_content = shipper_header.locator("xpath=following-sibling::dd").first
                shipper_name = shipper_content.inner_text()
                print(f"Shipper Information: {shipper_name}")
                return shipper_name
            else:
                print("Could not find 'Shipper' header element.")
                return None
                
        except Exception as e:
            print(f"Error extracting shipper info: {e}")
            return None

    def extract_shipment_info(self):
        """Extracts Pickup and Delivery locations from the shipment details page."""
        print("Extracting shipment information...")
        try:
            # Wait for map info windows or other indicators of addresses
            # Based on debug HTML, addresses are in gm-style-iw-d
            self.page.wait_for_selector(".gm-style-iw-d", timeout=10000)
            
            # Extract all addresses found in info windows
            address_elements = self.page.locator(".gm-style-iw-d")
            count = address_elements.count()
            
            addresses = []
            for i in range(count):
                text = address_elements.nth(i).inner_text()
                addresses.append(text.replace("\n", ", "))
            
            if len(addresses) >= 2:
                self.pickup_location = addresses[0]
                self.delivery_location = addresses[-1]
                print(f"Extracted Pickup Location: {self.pickup_location}")
                print(f"Extracted Delivery Location: {self.delivery_location}")
            else:
                print(f"Warning: Found {len(addresses)} addresses, expected at least 2. Addresses: {addresses}")
                self.pickup_location = addresses[0] if addresses else "Unknown"
                self.delivery_location = addresses[-1] if addresses else "Unknown"
                
        except Exception as e:
            print(f"Error extracting shipment info: {e}")
            self.pickup_location = "Unknown"
            self.delivery_location = "Unknown"

    def click_shipper_link(self):
        """Clicks the shipper link on the details page."""
        print("Locating and clicking Shipper link...")
        try:
            # Wait for loading to finish
            print("Waiting for page content to load...")
            try:
                self.page.wait_for_selector("text=Loading...", state="detached", timeout=10000)
            except:
                print("Warning: 'Loading...' did not detach or wasn't found.")
            
            # Wait a bit more for render
            time.sleep(2)

            # Locate the Shipper section
            # Structure: dt with "Shipper" -> sibling dd -> div -> div -> a
            shipper_header = self.page.locator("dt:has-text('Shipper')")
            if shipper_header.count() > 0:
                shipper_content = shipper_header.locator("xpath=following-sibling::dd").first
                shipper_link = shipper_content.locator("a").first
                
                shipper_name = shipper_link.inner_text()
                print(f"Found Shipper: {shipper_name}. Clicking link...")
                
                shipper_link.click()
                
                # Wait for navigation to user/shipper page
                try:
                    self.page.wait_for_load_state("domcontentloaded", timeout=10000)
                    # Wait for the "SOP" link or some profile content to appear
                    # We'll wait for a generic indicator if SOP isn't guaranteed
                    self.page.wait_for_selector("body", timeout=5000) 
                except:
                    print("Warning: domcontentloaded timed out, continuing...")
                
                print(f"Navigated to Shipper Page: {self.page.url}")
                
                # Dump HTML of shipper page for verification/inspection
                with open("shipper_page_debug.html", "w") as f:
                    f.write(self.page.content())
                print("Dumped shipper page HTML to shipper_page_debug.html")
                
            else:
                print("Could not find 'Shipper' header element.")
                
        except Exception as e:
            print(f"Error clicking shipper link: {e}")

    def navigate_to_sop(self):
        """Navigates to the SOP document from the shipper page."""
        print("Looking for SOP document...")
        try:
            # Wait for general loading
            try:
                self.page.wait_for_selector("text=Loading...", state="detached", timeout=5000)
            except:
                pass

            # Wait specifically for "Loading SOP..." to disappear
            print("Waiting for SOP section to load...")
            try:
                self.page.wait_for_selector("text=Loading SOP...", state="detached", timeout=15000)
            except:
                print("Warning: 'Loading SOP...' did not detach or wasn't found.")

            # Look for a link with text "SOP" or "Standard Operating Procedure"
            # Or look for a file link within the SOP section
            # Based on typical UI, it might be a filename or "View"
            # We'll search for any link in the SOP section if specific text fails
            
            sop_section = self.page.locator("[data-testid='shipper-sop-items']")
            if sop_section.count() > 0:
                # Try to find a link inside the SOP section
                sop_link = sop_section.locator("a").first
                if sop_link.count() == 0:
                     # Fallback: try to find text "SOP" link globally if not in section
                     sop_link = self.page.locator("a:has-text('SOP'), a:has-text('Standard Operating Procedure')").first
            else:
                 sop_link = self.page.locator("a:has-text('SOP'), a:has-text('Standard Operating Procedure')").first
            
            if sop_link.count() > 0:
                print(f"Found SOP link: {sop_link.inner_text()}. Clicking...")
                
                # Handle new tab
                with self.page.context.expect_page() as new_page_info:
                    sop_link.click()
                
                self.sop_page = new_page_info.value
                self.sop_page.wait_for_load_state("domcontentloaded")
                print(f"Navigated to SOP URL: {self.sop_page.url}")
                
                # Check for Google Sign-In
                if "accounts.google.com" in self.sop_page.url or "Sign in" in self.sop_page.title():
                    print("Google Sign-In detected.")
                    print("!!! USER ACTION REQUIRED !!!")
                    print("Please sign in to Google in the browser window.")
                    input("Press Enter in this terminal after you have successfully signed in and the Sheet is visible...")
                    
                    # After manual login, we expect to be on the sheet
                    print("Resuming...")
                
                # Wait for SOP content to load (Sheet)
                # Google Sheets takes a while to load the grid
                try:
                    # Wait for the grid or the main application container
                    self.sop_page.wait_for_selector("#docs-editor", timeout=30000) 
                except:
                    print("Warning: Timed out waiting for #docs-editor. Proceeding anyway...")
                    pass
                self.sop_page.wait_for_load_state("networkidle")
                
                # Dump SOP HTML for debugging/verification
                with open("sop_debug.html", "w") as f:
                    f.write(self.sop_page.content())
                print("Dumped SOP HTML to sop_debug.html")
                self.sop_page.wait_for_load_state("networkidle")
                
                # Dump SOP HTML for debugging/verification
                with open("sop_debug.html", "w") as f:
                    f.write(self.sop_page.content())
                print("Dumped SOP HTML to sop_debug.html")
            else:
                print("SOP link not found on shipper page.")
                # Dump page to see what's there
                with open("shipper_page_failed_sop.html", "w") as f:
                    f.write(self.page.content())
                print("Dumped shipper page to shipper_page_failed_sop.html")

        except Exception as e:
            print(f"Error navigating to SOP: {e}")

    def find_rate_card(self, pickup=None, delivery=None):
        """Finds the applicable rate card in the SOP using browser subagent for visual interpretation."""
        print("Searching for applicable rate card using browser agent...")
        
        # Switch to "Current Rates" tab if it exists
        try:
            print("Checking for 'Current Rates' tab...")
            rate_tab = self.sop_page.get_by_role("button", name="Current Rates")
            if rate_tab.count() > 0:
                print("Found 'Current Rates' tab. Clicking...")
                rate_tab.first.click()
                time.sleep(3)
            else:
                rate_tab = self.sop_page.locator("div[role='button']:has-text('Current Rates')")
                if rate_tab.count() > 0:
                    print("Found 'Current Rates' tab (alt selector). Clicking...")
                    rate_tab.first.click()
                    time.sleep(3)
                else:
                    print("'Current Rates' tab not found. Using current view.")
        except Exception as e:
            print(f"Error switching tabs: {e}")

        pickup = pickup or getattr(self, 'pickup_location', 'Unknown')
        delivery = delivery or getattr(self, 'delivery_location', 'Unknown')
        
        # Extract city names from addresses
        def extract_city(address):
            """Extract city name from full address"""
            if ',' in address:
                parts = [p.strip() for p in address.split(',')]
                if len(parts) >= 3:
                    return parts[1]
                elif len(parts) == 2:
                    return parts[1].split()[0] if parts[1] else parts[1]
            return address
        
        pickup_city = extract_city(pickup)
        delivery_city = extract_city(delivery)
        
        print(f"Using Pickup: {pickup} (searching for: {pickup_city})")
        print(f"Using Delivery: {delivery} (searching for: {delivery_city})")
        
        # Wait for sheet to render
        print("Waiting for sheet content to render...")
        time.sleep(5)
        
        # Take a screenshot for debugging
        try:
            self.sop_page.screenshot(path="google_sheet_debug.png")
            print("Captured screenshot: google_sheet_debug.png")
        except:
            pass
        
        # Use browser subagent to visually interpret and extract rate card data
        print("Launching browser subagent to interpret Google Sheet...")
        
        # The subagent will visually scan the sheet, find rows matching the locations,
        # and extract the rate information
        task_description = f"""
You are viewing a Google Sheets document with rate card information.

Your task:
1. Look at the visible spreadsheet cells
2. Find rows that contain "{pickup_city}" (the origin/pickup city) 
3. For matching rows, also check if they match "{delivery_city}" (the destination/delivery city)
4. Extract the rate/price information from the matching row(s)
5. Report back the rate card details you found

The sheet may have columns like: Origin, Destination, Rate, Service Type, etc.
Focus on finding rows where Origin matches "{pickup_city}" and Destination matches "{delivery_city}", or vice versa.

When you find a match, read the entire row and report all relevant information (rate, service type, any notes, etc.).

If you cannot find an exact match for both cities, report what you DO find (e.g., just origin match or just destination match).

Return when you have completed the search and extraction.
"""
        
        try:
            # Note: browser_subagent would work on the currently focused page
            # For this to work properly, we need to ensure the SOP page is the active context
            # Since we're in a separate page context (self.sop_page), we might need to bring it to front
            self.sop_page.bring_to_front()
            
            # Use browser_subagent - this will launch a reasoning agent that can see and interact with the page
            # The recording will capture its actions
            from playwright.sync_api import sync_playwright
            
            # For now, print instructions for manual extraction
            # TODO: Integrate actual browser_subagent when available in the playwright context
            print("\n" + "="*80)
            print("BROWSER AGENT TASK:")
            print("="*80)
            print(task_description)
            print("="*80)
            print("\nNote: Browser subagent integration requires additional setup.")
            print("For now, the Google Sheet is visible and ready for visual inspection.")
            print(f"Screenshot saved to: google_sheet_debug.png")
            print("\nThe agent should:")
            print(f"  1. Scroll through the 'Current Rates' tab")
            print(f"  2. Find rows matching: {pickup_city} → {delivery_city}")
            print(f"  3. Extract rate and related information")
            print("="*80)
            
        except Exception as e:
            print(f"Error using browser agent: {e}")
            import traceback
            traceback.print_exc()

    def close(self):
        """Closes the browser."""
        if self.context:
            self.context.close()
            print("Browser context closed.")
        elif hasattr(self, 'browser') and self.browser:
            self.browser.close()
            print("Browser closed.")

def main():
    agent = CargomaticAgent(headless=False)
    try:
        agent.start()

        # set username and password
        
        agent.login(username, password)
        
        # Search for the test shipment
        agent.search_global("AUT-201270")
        
        # Keep browser open for a bit to see results
        print("\n" + "="*80)
        print("Browser staying open for inspection...")
        print("The Google Sheet should be visible in 'Current Rates' tab")
        print("="*80)
        time.sleep(10)  # Give time for manual inspection or subagent access
        
    finally:
        # Comment out close to keep browser open for subagent
        # agent.close()
        pass

if __name__ == "__main__":
    main()
