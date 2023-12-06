def get_product_id(product_name:str, cursor:object) -> str|None:
    """Return product.id from its name"""
    cursor.execute(f"""SELECT id FROM product_table WHERE name = {product_name}""")
    row = cursor.fetchone()
    if not row:
        return None
    return cursor.fetchone()[0]
