from mysql import connector
from textdistance import ratcliff_obershelp
from .functions import get_product_id
from flask_server.functions import connect_mysql



def find_match(product_id:str, connection:object, arraysize:int=1000) -> tuple:
    """Find all product id that similiar to the product_id
    return 2-element tuple: first element is operation status and second element is data"""
    # Check database connection and if no connection made, make a new connetion
    try:
        cursor = connection.cursor()
        # Get product_name based on 'product_id'
        sql = f"""SELECT title FROM products WHERE id = {int(product_id)}"""
        cursor.execute(sql)
        product_name = cursor.fetchone()[0]
        if not product_name:
            raise Exception(f'No product with the id({product_id}) found')
        # Find the products with name close to the current product
        similiar_products_id = []
        similiar_products_name = []
        # Iterate through a big table
        cursor.execute(f"""SELECT id, name FROM product_table
                    WHERE name LIKE %{product_name}%""")
        while True:
            similiar_products = cursor.fetchmany(size=arraysize)
            if not similiar_products:
                break
            for similiar_proudct in similiar_products:
                similiar_products_id.append(similiar_proudct[0])
                similiar_products_name.append(similiar_proudct[1])
        # * After getting all similar products, we can score them and sort them by this score. But it's the matter yet!
        return (1, similiar_products_id)
    except Exception as e:
        print('Error in finding match: ', e.__str__())
        return (None, e.__str__())
    