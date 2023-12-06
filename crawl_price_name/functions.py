"""NOTE: Thousand separator character in english is ','. but in persian it is '٬'. They are diffrent. Some keyboards could not input this type of unicode.
but its unicode number is '1644' while english thousand separator is '48'. So we have used builtin function 'chr' to convert its code to unicode"""
import re



# * External functions
def convert_to_english(text)-> str|None:
    """Convert persian letters to english then return only numbers"""
    persian_to_english = {
        '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4',
        '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9',
        # Add more mappings for other Persian characters if needed
    }
    converted_text = ''
    for char in text:
        if char in persian_to_english:
            converted_text += persian_to_english[char]
        else:
            converted_text += char
    # Remove non-numeric characters
    converted_text = ''.join(c for c in converted_text if c.isdigit())
    # If converted_text len is longer than 10 characters, it mean the founded price is wrong
    if len(converted_text) > 9 or len(converted_text) < 4:
        return None
    return converted_text




# * Internal functions

def combine_parse_convert_tag(tag) -> str:
    """First convert persian digits to english then parse tag text to extract price"""
    price_list = []
    tag_text = tag.text
    converted_text = ''
    persian_to_english = {
        '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4',
        '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9',
        # Add more mappings for other Persian characters if needed
    }
    converted_text = ''
    for char in tag_text:
        if char in persian_to_english:
            converted_text += persian_to_english[char]
        else:
            converted_text += char
    price_list = check_tag_text(converted_text, price_list)
    if price_list:
        try:
            return min(price_list)
        except Exception as e:
            print('Error in "parse_del_tag" function: ', e.__str__())
    # else:
    #     print('No price tags found!')
    return 0



def find_price_in_meta_tags(beautiful_soup_object:object,  price_set:set) -> set:
    """Try to find any price in 'meta' tag and return price_set contains only smallest price if any price found in the meta tags"""
    meta_tags = beautiful_soup_object.select('meta')
    for mt in meta_tags:
        # Try to extract price from 'name' attribute of the meta tag
        mt_name = mt.get('name', None)
        if mt_name:
            if 'price' in mt_name or 'Price' in mt_name:
                mt_price = mt.get('content', None)
                if mt_price:
                    try:
                        price_set.add(int(convert_to_english(mt_price)))
                    except Exception:
                        pass
        # Try to extract price from 'itemprop' attribute of the meta tag
        mt_itemprop = mt.get('itemprop', None)
        if mt_itemprop:
            if 'price' in mt_itemprop or 'Price' in mt_itemprop:
                mt_price = mt.get('content', None)
                if mt_price:
                    try:
                        price_set.add(int(convert_to_english(mt_itemprop)))
                    except Exception:
                        pass
    # If found several prices in meta price tags, only let the smallest price remains in the price_set
    if price_set:
        if 0 in price_set:
            price_set.remove(0)
        _smallest_price = min(price_set)
        price_set.clear()
        price_set.add(_smallest_price)
    return price_set


def meta_availability_tag(beautiful_soup_object:object) -> bool|None:
    """Check 'og:availability' in <meta> tag to find if product is available or not.
    If returns True it means product is available.
    If returns False means product is not available.
    If returns None means this tag is unavailable or 'content' value is unexpected"""
    meta_tags = beautiful_soup_object.select('meta')
    for mt in meta_tags:
        # Check property attribute of meta tag
        meta_propery = mt.attrs.get('property', None)
        if meta_propery == 'og:availability':
            meta_og_availability = mt.attrs.get('content', None)
            if meta_og_availability:
                if meta_og_availability in ['in stock', 'instock']:
                    return True
                if meta_og_availability in ['out of stock', 'outofstock']:
                    return False
        # Check name attribute of meta tag
        else:
            meta_name = mt.attrs.get('name', None)
            if meta_name == 'availability':
                meta_og_availability = mt.attrs.get('content', None)
                if meta_og_availability:
                    if meta_og_availability in ['in stock', 'instock']:
                        return True
                    if meta_og_availability in ['out of stock', 'outofstock']:
                        return False
    return None



def is_product_available(tag_text:str) -> bool:
    """Check if product is available by common patterns for available products in the websites"""
    # Some site like esam also have 'ثبت پیشنهاد' for product price
    common_availability_text = ['اضافه به سبد خرید', 'اضافه به سبدخرید', 'افزودن به سبد خرید', 'افزودن به سبدخرید',
                                'سبد خرید', 'سبدخرید', 'کالا موجود است',
                                'خرید اقساطی', 'خرید', 'خرید کالا',
                                'خرید', 'ثبت پیشنهاد', 'افزودن به کارت خرید',
                                'موجود در انبار', 'در انبار موجود است']
    result = [elem for elem in common_availability_text if (elem in tag_text)]
    if bool(result):
        return True
    return False


def is_product_not_available(tag_text:str) -> bool:
    """Check if product is not available by common patterns for unavailable products in the websites"""
    # In some websites, price is available but add to cart button disabled by JS, But there is a button with text 'به من اطلاع بده'
    common_unavailability_text = ['اطلاع بده', 'تماس بگیرید', 'موجود نیست',
                                  'ناموجود', 'اتمام موجودی', 'در انبار موجود نمی باشد',]
    result = [elem for elem in common_unavailability_text if (elem in tag_text)]
    if bool(result):
        return True
    return False



def check_tag_text(tag_text:str, price_list:list) -> list:
    """Helper function to find price value from a tag text and put it in a list"""
    tag_text = tag_text.strip()
    # Some websites like 'esam.ir' has ':' in price tag. replace ':' with ' '
    if ':' in tag_text:
        tag_text = tag_text.replace(':', ' ')
    # If there is space in text, split the text into independent words and check them separately
    if '\xa0' in tag_text:
        tag_text = tag_text.replace('\xa0', ' ')
    # print('price_tag_text: ', tag_text)
    if ' ' in tag_text:
        tag_texts = [tag_text.strip() for tag_text in tag_text.split(' ')]
        for single_text in tag_texts:
            # print(single_text, ' ---> ', len(single_text))
            if single_text.replace(',', '').isdigit() and (',' in single_text or chr(1644) in single_text):
                price_list.append(int(single_text.replace(',', '')))
            elif single_text.replace(chr(1644), '').isdigit() and (',' in single_text or chr(1644) in single_text):
                price_list.append(int(single_text.replace(chr(1644), '')))
            elif single_text.replace(chr(1643), '').isdigit() and (',' in single_text or chr(1643) in single_text):
                price_list.append(int(single_text.replace(chr(1643), '')))
            # Maybe thousand separator is '.' rather than ','
            elif single_text.replace('.', '').isdigit() and ('.' in single_text):
                price_list.append(int(single_text.replace('.', '')))
    # Check every text indepentenly and it the text is a price with thousand separator, add it to the list price
    elif tag_text.replace(',', '').isdigit() and (',' in tag_text or chr(1644) in tag_text):
        price_list.append(int(tag_text.replace(',', '')))
    elif tag_text.replace(chr(1644), '').isdigit() and (',' in tag_text or chr(1644) in tag_text):
        price_list.append(int(tag_text.replace(chr(1644), '')))
    elif tag_text.replace(chr(1643), '').isdigit() and (',' in tag_text or chr(1643) in tag_text):
                price_list.append(int(tag_text.replace(chr(1643), '')))
    # Maybe thousand separator is '.' rather than ','
    elif tag_text.replace('.', '').isdigit() and ('.' in tag_text):
        price_list.append(int(tag_text.replace('.', '')))
    # If price is attached to another text and could not be accessed separately, process the price and separate it from the attched text
    elif (',' in tag_text or chr(1644) in tag_text):
        try:
            possible_number = re.findall(r'\d+', tag_text.replace(',', '').replace(chr(1644), ''))
            if possible_number[0].isdigit():
                price_list.append(int(possible_number[0]))
        except Exception:
            pass
    return price_list


def parse_del_tag(soup:object) -> str:
    """If any price has line-through before discount price, find them and return the minimum of them
    https://stackoverflow.com/questions/10993612/how-to-remove-xa0-from-string-in-python"""
    before_discount_price_list = []
    del_tags = soup.find_all('del')
    if del_tags:
        for del_tag in del_tags:
            # Sometimes in a 'del' tag there are more text than just price separated with a space ' '
            # ! In python string, '\xa0' is added as non-breaking space in python code. It is given when there is 
            del_text = del_tag.text
            before_discount_price_list = check_tag_text(del_text, before_discount_price_list)
        if before_discount_price_list:
            try:
                return min(before_discount_price_list)
            except Exception as e:
                print('Error in "parse_del_tag" function: ', e.__str__())
    else:
        pass
        # print('No <del> tags found!')
    return '0'


def parse_bdi_tag(soup: object) -> str:
    """Some non-english websites has their prices in <bdi> tag. pars every bdi tag and return min prices"""
    prices_list = []
    bdi_tags = soup.find_all('bdi')
    if bdi_tags:
        for bdi_tag in bdi_tags:
            # Sometimes in a 'bdi' tag there are more text than just price separated with a space ' '
            # ! In python string, '\xa0' is added as non-breaking space in python code. It is given when there is
            bdi_text = bdi_tag.text
            prices_list = check_tag_text(bdi_text, prices_list)
        if prices_list:
            try:
                return min(prices_list)
            except Exception as e:
                print('Error in "parse_bdi_tag" function: ', e.__str__())
    else:
        # print('No <bdi> tags found!')
        pass
    return 0


def parse_ins_tag(soup: object) -> str:
    """Some websites has their price in <ins> tag. parse all ins tags and return the min value found"""
    prices_list = []
    ins_tags = soup.find_all('ins')
    if ins_tags:
        for ins_tag in ins_tags:
            # Sometimes in a 'ins' tag there are more text than just price separated with a space ' '
            # ! In python string, '\xa0' is added as non-breaking space in python code. It is given when there is 
            ins_text = ins_tag.text
            prices_list = check_tag_text(ins_text, prices_list)
        if prices_list:
            try:
                return min(prices_list)
            except Exception as e:
                print('Error in "parse_bdi_tag" function: ', e.__str__())
    else:
        # print('No <bdi> tags found!')
        pass
    return 0


def parse_tag(tag:object) -> str:
    """Parse the beautifulsoup tag object content and find if there are any price in it. if not found, return 0"""
    price_list = []
    tag_text = tag.text
    price_list = check_tag_text(tag_text, price_list)
    if price_list:
        try:
            return min(price_list)
        except Exception as e:
            print('Error in "parse_del_tag" function: ', e.__str__())
    # else:
    #     print('No price tags found!')
    return 0


def parse_price_tag(attr_value:str) -> bool:
    """Check the price tag attributes and tell if this tag really related to price or not"""
    filter_list = ['compare', 'Compare', 'currency', 'Currency', 'symbole', 'Symbole', 'better', 'Better']
    result = [elem for elem in filter_list if (elem in attr_value)]
    if bool(result):
        return False
    return True



# ???? Torob and Emalls extract_prices ????
"""
'_torob_extract_price' and '_emalls_extract_price' and '_digikala_extract_price' are exactly the same but in future they might not be the same
"""

def _digikala_extract_price(price_tags:list, prices:set) -> set:
    """Helper function to extract price from price related elements"""
    prices_text = []
    for price_tag in price_tags:
        prices_text.append(price_tag.text)
    if prices_text:
        for pt in prices_text:
            if '\xa0' in pt:
                pt = pt.replace('\xa0', ' ')
            if ' ' in pt:
                pt = pt.strip()
            if ' ' in pt:
                for pt_parted in pt.split():
                    if ',' in pt_parted or chr(1644) in pt_parted:
                        pt_parted = pt_parted.replace(',', '').replace(chr(1644), '').replace(chr(1643), '')
                        if pt_parted.isdigit():
                            prices.add(int(pt_parted))
            else:
                if ',' in pt or chr(1644) in pt:
                    pt = pt.replace(',', '').replace(chr(1644), '').replace(chr(1643), '')
                    if pt.isdigit():
                        prices.add(int(pt))
    return prices


def _torob_extract_price(price_tags:list, prices:set) -> set:
    """Helper function to extract price from price related elements"""
    prices_text = []
    for price_tag in price_tags:
        prices_text.append(price_tag.text)
    if prices_text:
        for pt in prices_text:
            if '\xa0' in pt:
                pt = pt.replace('\xa0', ' ')
            if ' ' in pt:
                pt = pt.strip()
            if ' ' in pt:
                for pt_parted in pt.split(' '):
                    if ',' in pt_parted or chr(1644) in pt_parted or chr(1643) in pt_parted:
                        pt_parted = pt_parted.replace(',', '').replace(chr(1644), '').replace(chr(1643), '')
                        if pt_parted.isdigit():
                            prices.add(int(pt_parted))
            else:
                if ',' in pt or chr(1644) in pt or chr(1643) in pt:
                    pt = pt.replace(',', '').replace(chr(1644), '').replace(chr(1643), '')
                    if pt.isdigit():
                        prices.add(int(pt))
    return prices


def _emalls_extract_price(price_tags:list, prices:set) -> set:
    """Helper function to extract price from price related elements"""
    prices_text = []
    for price_tag in price_tags:
        prices_text.append(price_tag.text)
    # print(prices_text)
    if prices_text:
        for pt in prices_text:
            if '\xa0' in pt:
                pt = pt.replace('\xa0', ' ')
            if ' ' in pt:
                pt = pt.strip()
            if ' ' in pt:
                for pt_parted in pt.split():
                    if ',' in pt_parted or chr(1644) in pt_parted:
                        pt_parted = pt_parted.replace(',', '').replace(chr(1644), '').replace(chr(1643), '')
                        if pt_parted.isdigit():
                            prices.add(int(pt_parted))
            else:
                if ',' in pt or chr(1644) in pt:
                    pt = pt.replace(',', '').replace(chr(1644), '').replace(chr(1643), '')
                    if pt.isdigit():
                        prices.add(int(pt))
    return prices
