# -*- coding: utf-8 -*-
# Zillow scraper functions, these are sourced at the top of zillow_runfile.py

import re as re
import time
import zipcode
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException
from bs4 import BeautifulSoup
from scipy import misc
import urllib2
import cStringIO
import os
import pandas as pd

image_directory = "F:\\Zillow Project\\Images\\"

#create list of zipcodes by condition
def zipcodes_list(st_items):
    # If st_items is a single zipcode string.
    if type(st_items) == str:
        zcObjects = zipcode.islike(st_items)
        output = [str(i).split(" ", 1)[1].split(">")[0] 
                    for i in zcObjects]
    # If st_items is a list of zipcode strings.
    elif type(st_items) == list:
        zcObjects = [n for i in st_items for n in zipcode.islike(str(i))]
        output = [str(i).split(" ", 1)[1].split(">")[0] 
                    for i in zcObjects]
    else:
        raise ValueError("input 'st_items' must be of type str or list")
    return(output)

#create driver
def init_driver(filepath):
    driver = webdriver.Chrome(executable_path = filepath)
    driver.wait = WebDriverWait(driver, 10)
    return(driver)

#go to website
def navigate_to_website(driver, site):
    driver.get(site)

#hit the buy button
def click_buy_button(driver):
    try:
        button = driver.wait.until(EC.element_to_be_clickable(
            (By.CLASS_NAME, "nav-header")))
        button.click()
        time.sleep(10)
    except (TimeoutException, NoSuchElementException):
        raise ValueError("Clicking the 'Buy' button failed")

#enter the zipcode into the field
def enter_search_term(driver, search_term):
    try:
        searchBar = driver.wait.until(EC.presence_of_element_located(
            (By.ID, "citystatezip")))
        button = driver.wait.until(EC.element_to_be_clickable(
            (By.CLASS_NAME, "zsg-icon-searchglass")))
        searchBar.clear()
        time.sleep(3)
        searchBar.send_keys(search_term)
        time.sleep(3)
        button.click()
        time.sleep(3)
        return(True)
    except (TimeoutException, NoSuchElementException):
        return(False)

def checkProperListingTypes(driver):
    try:
        #hit the listing types button
        listingTypes = driver.wait.until(EC.presence_of_element_located(
                (By.ID, "listings-menu-label")))
        #for sale listings button
        forSale_listings = driver.wait.until(EC.presence_of_element_located(
                (By.ID, "fs-listings")));
        #potential listings button
        potential_listings = driver.wait.until(EC.presence_of_element_located(
                (By.ID, "pm-listings")));
        #for rent listings button
        rent_listings = driver.wait.until(EC.presence_of_element_located(
                (By.ID, "fr-listings")));
        #sold listings button
        recentlySold_listings = driver.wait.until(EC.presence_of_element_located(
                (By.ID, "rs-listings")));
        #hit listing type and wait
        listingTypes.click()
        time.sleep(3)
        #check only For Sale and Recently Sold
        if forSale_listings.get_attribute("class") != "listing-type selected":
            checkbox = driver.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "#fs-listings .listing-category")))
            checkbox.click()
            time.sleep(3)
        
        if potential_listings.get_attribute("class") == "listing-type selected":
            checkbox = driver.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "#pm-listings .listing-category")))
            checkbox.click()
            time.sleep(3)    
        
        if rent_listings.get_attribute("class") == "listing-type selected":
            checkbox = driver.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "#fr-listings .listing-category")))
            checkbox.click()
            time.sleep(3)
            
        if recentlySold_listings.get_attribute("class") != "listing-type selected":
            checkbox = driver.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "#rs-listings .listing-category")))
            checkbox.click()
            time.sleep(3)
        #close listing types    
        listingTypes.click()
        return(True)
    except (TimeoutException, NoSuchElementException):
        return(False)
    

def results_test(driver):
    # Check to see if there are any returned results
    try:
        no_results = driver.find_element_by_css_selector(
            '.zoom-out-message').is_displayed()
    except (NoSuchElementException, TimeoutException):
        # Check to see if the zipcode is invalid or not
        try:
            no_results = driver.find_element_by_class_name(
                'zsg-icon-x-thick').is_displayed()
        except (NoSuchElementException, TimeoutException):
            no_results = False
    return(no_results)

    


def get_html(driver):
    output = []
    keep_going = True
    while keep_going:
        # Pull page HTML
        try:
            output.append(driver.page_source)
        except TimeoutException:
            pass
        try:
            # Check to see if a "next page" link exists
            keep_going = driver.find_element_by_class_name(
                'zsg-pagination-next').is_displayed()
        except NoSuchElementException:
            keep_going = False
        if keep_going:
            # Test to ensure the "updating results" image isnt displayed. 
            # Will try up to 5 times before giving up, with a 5 second wait 
            # between each try. 
            tries = 5
            try:
                cover = driver.find_element_by_class_name(
                    'list-loading-message-cover').is_displayed()
            except (TimeoutException, NoSuchElementException):
                cover = False
            while cover and tries > 0:
                time.sleep(5)
                tries -= 1
                try:
                    cover = driver.find_element_by_class_name(
                        'list-loading-message-cover').is_displayed()
                except (TimeoutException, NoSuchElementException):
                    cover = False
            # If the "updating results" image is confirmed to be gone 
            # (cover == False), click next page. Otherwise, give up on trying 
            # to click thru to the next page of house results, and return the 
            # results that have been scraped up to the current page.
            if cover == False:
                try:
                    driver.wait.until(EC.element_to_be_clickable(
                        (By.CLASS_NAME, 'zsg-pagination-next'))).click()
                    time.sleep(3)
                except TimeoutException:
                    keep_going = False
            else:
                keep_going = False
    return(output)

def get_listings(list_obj):
    # Split the raw HTML into segments, one for each listing.
    output = []
    for i in list_obj:
        htmlSplit = i.split('" id="zpid_')[1:]
        output += htmlSplit
    print(str(len(output)) + " home listings scraped\n***")
    return(output)


def processListing(driver, zpid, listURL, index, engine):
    
    
    #get html and convert it to nice soup
    soup = BeautifulSoup(driver.page_source, "lxml")
    
    #store the new listing in dataframe
    new_obs = []
    
    
    #add zpid and url
    new_obs.append(zpid)
    new_obs.append(listURL)
    new_obs.append(index)
    
    
    # Street Address
    new_obs.append(get_street_address(soup))
    
    
    # Bathrooms
    new_obs.append(get_bathrooms(soup))
        
    # Bedrooms
    new_obs.append(get_bedrooms(soup))
    
    #getting the interior features card
    interiorFeatures = getInterriorFeatures(soup)
    
    #process the interior features card - heating, cooling, flooring, roomcount
    if(interiorFeatures != "NA"):
        new_obs.append(getHeating(interiorFeatures))
        new_obs.append(getCooling(interiorFeatures))
        new_obs.append(getFloorSize(interiorFeatures))
        new_obs.append(getRoomCount(interiorFeatures))
    else:
        new_obs.extend(["NA", "NA", "NA", "NA"])
        
    # Building unit count
    new_obs.append(getUnitCount(soup))
    
    #getting the construction features card
    constructionFeatures = getConstructionInfo(soup)
    
    #process construction features - Style, Dates, Roof, Exterior    
    if(constructionFeatures != "NA"):
        new_obs.append(getStyle(constructionFeatures))
        new_obs.append(getRoofType(constructionFeatures))
        new_obs.append(getExteriorMaterial(constructionFeatures))
        new_obs.append(getConstrDates(constructionFeatures))
    else:
        new_obs.extend(["NA", "NA", "NA", "NA"])
    
    #getting the exterior features card    
    extFeatures = getExteriorFeatures(soup)
    
    #processing exterior features - patio, lot, floor
    if(extFeatures != "NA"):
        new_obs.append(getPatio(extFeatures))
        new_obs.append(getLot(extFeatures))
        new_obs.append(getFloor(extFeatures))
    else:
        new_obs.extend(["NA", "NA", "NA"])
        
    #getting parking
    new_obs.append(getParking(soup))
    
    #getting HOA fee
    new_obs.append(getHOA(soup))

    #get activity on zillow card
    activityCard = getActivityCard(soup)
    
    #processing activity on zillow - days on zillow, shoppers saved
    if(activityCard != "NA"):
        new_obs.append(getDaysOnZillow(activityCard))
        new_obs.append(getShoppersSaved(activityCard))
    else:
        new_obs.extend(["NA", "NA"])
    
    #getting price
    new_obs.append(getPrice(soup))
    #getting zestimate
    new_obs.append(getZestimate(soup))
    
    #add text description
    new_obs.append(getTextDescr(soup))
    
    
    print("Getting price history")
    pricesAdded = getPriceHistory(driver, zpid, engine)
    if str(pricesAdded)=="NA":
        print("Failed to get price history")
    else:
        print(str(pricesAdded) + " price entries added")
    
    #getting final html
    html = BeautifulSoup(driver.page_source, "lxml")
    new_obs.append(html)
    
    print("Processing images")
    try:
        driver.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "#hip-content .photo-wall-content .sm-tile .img-wrapper .hip-photo")))
        imagesProcessed = getImages(driver, zpid)
    except (TimeoutException, NoSuchElementException):
        imagesProcessed = "NA"
    
    if(str(imagesProcessed) == "NA"):
        print("Failed to obtain images")
    else:
        print(str(imagesProcessed) + " images saved")
        
    return new_obs

def getPriceHistory(driver, zpid, engine):
    try:
        dfPrice = pd.DataFrame({'zpid': [],
                       'date' : [],
                       'event' : [],
                       'price' : []
                       }, columns = ['zpid',
                        'date',
                        'event',
                       'price'])
        
        driver.wait.until(EC.element_to_be_clickable(
                        (By.XPATH, "//*[contains(text(), 'Price / Tax History')]//..")))
        
        soup_obj = BeautifulSoup(driver.page_source, "lxml")
        priceTable = soup_obj.find(text=re.compile("Price History")).parent.next_sibling
        if priceTable is None:
            priceTable = soup_obj.find(text=re.compile("Price History")).next_sibling
        
        if priceTable is None:
            #expanding price history
            try:
                button = driver.wait.until(EC.element_to_be_clickable(
                        (By.XPATH, "//*[contains(text(), 'Price / Tax History')]//..")))
                button.click()
                driver.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "#hdp-price-history .zsg-table")))
            except (TimeoutException, NoSuchElementException):
                print("Failed to expand price history")
            #continuing as before
            soup_obj = BeautifulSoup(driver.page_source, "lxml")
            priceTable = soup_obj.find(id="hdp-price-history").find(class_="zsg-table")
        
        priceRecords = priceTable.tbody.find_all("tr")
        
        for price in priceRecords:
            try:
                new_obs = []
                objects = price.find_all("td")
                new_obs.append(zpid)
                #date
                new_obs.append(objects[0].get_text())
                #event
                new_obs.append(objects[1].get_text())
                #price
                new_obs.append(objects[2].span.get_text().strip())
                dfPrice.loc[len(dfPrice.index)] = new_obs
            except:
                continue
        
        dfPrice.to_sql(name='pricehistory', con=engine, if_exists = 'append', index=False)
        return len(dfPrice)
    except (ValueError, AttributeError):
        return "NA"


def getImages(driver,zpid):
    try:
        i = 1
        soup_obj = BeautifulSoup(driver.page_source, "lxml")
        imageRoot = soup_obj.find(class_="photo-wall yui3-widget yui3-photocarousel yui3-photocarouselwall")
        imagesAll = imageRoot.find_all(class_="sm-tile")
        for image in imagesAll:
            time.sleep(0.1)
            imageNode = image.find(class_="hip-photo")
            if imageNode is not None:
                #it seems like /p_c/ points to small version of image
                #and /p_f/ points to large version
                if imageNode.has_attr('src'):
                    imageUrl = imageNode['src'].replace('/p_c/','/p_f/')
                elif imageNode.has_attr('href'):
                    imageUrl = imageNode['href'].replace('/p_c/','/p_f/')
                else:
                    continue
                try:
                    f = cStringIO.StringIO(urllib2.urlopen(imageUrl).read())
                except:
                    continue
                try :
                    imageBlob = misc.imread(f)
                except:
                    imageBlob = None
                if imageBlob is not None:
                    if not os.path.exists(image_directory + str(zpid)):
                        os.makedirs(image_directory + str(zpid))
                    misc.imsave(image_directory + str(zpid) + '\\' + str(i)+'.jpg', imageBlob)
                    i+=1
    except (ValueError, AttributeError):
        i = "NA"
    return(i)

def getTextDescr(soup_obj):
    try:
        text = soup_obj.find(property="zillow_fb:description")['content']
    except (ValueError, AttributeError):
        text = "NA"
    if len(text) == 0 or text == "null":
        text = "NA"
    return(text)

def getZestimate(soup_obj):
    try:
        homeValWrap = soup_obj.find(id="home-value-wrapper")
        zestimate = homeValWrap.find(text = "Zestimate").parent.parent.find(class_="value-suffix").previous_sibling
    except (ValueError, AttributeError):
        zestimate = "NA"
    if len(zestimate) == 0 or zestimate == "null":
        zestimate = "NA"
    return(zestimate)    

def getPrice(soup_obj):
    try:
        price = soup_obj.find(property="product:price:amount")["content"]
    except (ValueError, AttributeError, TypeError):
        price = "NA"
    if len(price) == 0 or price == "null":
        price = "NA"
    return(price)

def getShoppersSaved(soup_obj):
    try:
        shoppers = soup_obj.find(class_="hdp-fact-value", text=re.compile(" shoppers saved this home")).get_text()
        shoppers = shoppers[0:shoppers.find(" shoppers saved this home")]
    except (ValueError, AttributeError):
        shoppers = "NA"
    if len(shoppers) == 0 or shoppers == "null":
        shoppers = "NA"
    return(shoppers)


def getDaysOnZillow(soup_obj):
    try:
        days = soup_obj.find(class_="hdp-fact-name", text="Days on Zillow: ").next_sibling.get_text()
        days = days[0:days.find(" days on Zillow")]
    except (ValueError, AttributeError):
        days = "NA"
    if len(days) == 0 or days == "null":
        days = "NA"
    return(days)


def getActivityCard(soup_obj):
    try:
        activity = soup_obj.find(class_="hdp-fact-category-heading", text="Activity On Zillow").next_sibling
    except (ValueError, AttributeError):
        activity = "NA"
    if len(activity) == 0 or activity == "null":
        activity = "NA"
    return(activity)


def getParking(soup_obj):
    try:
        card = soup_obj.find(class_="hdp-fact-category-heading", text="Parking").next_sibling
        parking = card.find(class_="hdp-fact-name", text="Parking: ").next_sibling.get_text()
    except (ValueError, AttributeError):
        parking = "NA"
    if len(parking) == 0 or parking == "null":
        parking = "NA"
    return(parking)


def getHOA(soup_obj):
    try:
        card = soup_obj.find(class_="hdp-fact-category-heading", text="Finance").next_sibling
        hoa = card.find(class_="hdp-fact-name", text="HOA Fee: ").next_sibling.get_text()
    except (ValueError, AttributeError):
        hoa = "NA"
    if len(hoa) == 0 or hoa == "null":
        hoa = "NA"
    return(hoa)

def getFloor(soup_obj):
    try:
        floor = soup_obj.find(class_="hdp-fact-name", text="Unit floor #: ").next_sibling.get_text()
    except (ValueError, AttributeError):
        floor = "NA"
    if len(floor) == 0 or floor == "null":
        floor = "NA"
    return(floor)

def getLot(soup_obj):
    try:
        lot = soup_obj.find(class_="hdp-fact-name", text="Lot: ").next_sibling.get_text()
    except (ValueError, AttributeError):
        lot = "NA"
    if len(lot) == 0 or lot == "null":
        lot = "NA"
    return(lot)


def getPatio(soup_obj):
    try:
        patioCard = soup_obj.find(class_="hdp-fact-category", text="Patio").next_sibling
        patio = patioCard.find(class_="hdp-fact-value").get_text()
    except (ValueError, AttributeError):
        patio = "NA"
    if len(patio) == 0 or patio == "null":
        patio = "NA"
    return(patio)


def getExteriorFeatures(soup_obj):
    try:
        features = soup_obj.find(class_="hdp-fact-category-heading", text="Exterior Features").next_sibling
    except (ValueError, AttributeError):
        features = "NA"
    if len(features) == 0 or features == "null":
        features = "NA"
    return(features)


def getStyle(soup_obj):
    try:
        TypeStyle = soup_obj.find(class_="hdp-fact-category", text="Type and Style").next_sibling
        style = TypeStyle.find(class_="hdp-fact-value").get_text()
    except (ValueError, AttributeError):
        style = "NA"
    if len(style) == 0 or style == "null":
        style = "NA"
    return(style)

def getRoofType(soup_obj):
    try:
        materials = soup_obj.find(class_="hdp-fact-category", text="Materials").next_sibling
        roof = materials.find(class_="hdp-fact-name", text="Roof type: ").next_sibling.get_text()
    except (ValueError, AttributeError):
        roof = "NA"
    if len(roof) == 0 or roof == "null":
        roof = "NA"
    return(roof)

def getExteriorMaterial(soup_obj):
    try:
        materials = soup_obj.find(class_="hdp-fact-category", text="Materials").next_sibling
        exterior = materials.find(class_="hdp-fact-name", text="Exterior material: ").next_sibling.get_text()
    except (ValueError, AttributeError):
        exterior = "NA"
    if len(exterior) == 0 or exterior == "null":
        exterior = "NA"
    return(exterior)

def getConstrDates(soup_obj):
    try:
        dates = soup_obj.find(class_="hdp-fact-category", text="Dates").next_sibling
        constDate = dates.find(class_="hdp-fact-value").get_text()
    except (ValueError, AttributeError):
        constDate = "NA"
    if len(constDate) == 0 or constDate == "null":
        constDate = "NA"
    return(constDate)


def getConstructionInfo(soup_obj):
    try:
        features = soup_obj.find(class_="hdp-fact-category-heading", text="Construction").next_sibling
    except (ValueError, AttributeError):
        features = "NA"
    if len(features) == 0 or features == "null":
        features = "NA"
    return(features)

def getUnitCount(soup_obj):
    try:
        building = soup_obj.find(class_="hdp-fact-category-heading", text="Building").next_sibling
        unitCount = building.find(class_="hdp-fact-name", text="Unit count: ").next_sibling.get_text()
    except (ValueError, AttributeError):
        unitCount = "NA"
    if len(unitCount) == 0 or unitCount == "null":
        unitCount = "NA"
    return(unitCount)


def getInterriorFeatures(soup_obj):
    try:
        features = soup_obj.find(class_="hdp-fact-category-heading", text="Interior Features").next_sibling
    except (ValueError, AttributeError):
        features = "NA"
    if len(features) == 0 or features == "null":
        features = "NA"
    return(features)

def getHeating(soup_obj):
    try:
        heating = soup_obj.find(class_="hdp-fact-name", text="Heating: ").next_sibling.get_text()
    except (ValueError, AttributeError):
        heating = "NA"
    if len(heating) == 0 or heating == "null":
        heating = "NA"
    return(heating)

def getCooling(soup_obj):
    try:
        cooling = soup_obj.find(class_="hdp-fact-name", text="Cooling: ").next_sibling.get_text()
    except (ValueError, AttributeError):
        cooling = "NA"
    if len(cooling) == 0 or cooling == "null":
        cooling = "NA"
    return(cooling)

def getFloorSize(soup_obj):
    try:
        floorSize = soup_obj.find(class_="hdp-fact-name", text="Floor size: ").next_sibling.get_text()
    except (ValueError, AttributeError):
        floorSize = "NA"
    if len(floorSize) == 0 or floorSize == "null":
        floorSize = "NA"
    return(floorSize)

def getRoomCount(soup_obj):
    try:
        roomCount = soup_obj.find(class_="hdp-fact-name", text="Room count: ").next_sibling.get_text()
    except (ValueError, AttributeError):
        roomCount = "NA"
    if len(roomCount) == 0 or roomCount == "null":
        roomCount = "NA"
    return(roomCount)

def get_street_address(soup_obj):
    try:
        street = soup_obj.find(property="og:zillow_fb:address")['content']
    except (ValueError, AttributeError):
        street = "NA"
    if len(street) == 0 or street == "null":
        street = "NA"
    return(street)
    
def get_bathrooms(soup_obj):
    try:
        bath = soup_obj.find(property="zillow_fb:baths")['content']
    except (ValueError, AttributeError):
        bath = "NA"
    if len(bath) == 0 or bath == "null":
        bath = "NA"
    return(bath)

def get_bedrooms(soup_obj):
    try:
        bed = soup_obj.find(property="zillow_fb:beds")['content']
    except (ValueError, AttributeError):
        bed = "NA"
    if len(bed) == 0 or bed == "null":
        bed = "NA"
    return(bed)


def getZpid(url):
    try:
        reversedURL = url[::-1]
        start = reversedURL.index( '/dipz' ) + len( '/dipz' )
        end = reversedURL.index( '/', start )
        zpid = reversedURL[start+1:end]
        return zpid[::-1]
    except ValueError:
        return ""
        
#getting the url of listing
def get_url(soup_obj):
    # Try to find url in the BeautifulSoup object.
    href = [n["href"] for n in soup_obj.find_all("a", href = True)]
    url = [i for i in href if "homedetails" in i]
    if len(url) > 0:
        url = "http://www.zillow.com/homes/for_sale/" + url[0]
    else:
        # If that fails, contruct the url from the zpid of the listing.
        url = [i for i in href if "zpid" in i and "avorite" not in i]
        if len(url) > 0:
            zpid = re.findall(r"\d{8,10}", href[0])
            if zpid is not None and len(zpid) > 0:
                url = 'http://www.zillow.com/homes/for_sale/' \
                        + str(zpid[0]) \
                        + '_zpid/any_days/globalrelevanceex_sort/29.759534,' \
                        + '-95.335321,29.675003,-95.502863_rect/12_zm/'
            else:
                url = "NA"
        else:
            url = "NA"
    return(url)

def close_connection(driver):
    driver.quit()
