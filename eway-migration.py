from woocommerce import API
import pymysql
import pandas as pd
from sshtunnel import SSHTunnelForwarder
import mysql.connector
from datetime import datetime
import time

# update this to your table prefix
table_prefix = 'wp_'
# ssh host
ssh_host = 'xxx.xxx.xxx.xxx'
# your ssh port, update this
ssh_port = 12345
ssh_user = 'SSH_USER'
ssh_password = '***********'
mysql_host = '127.0.0.1'
mysql_port = 3306
mysql_user = 'MYSQL_USER'
mysql_dbname = 'MYSQL_DBNAME'
mysql_pwd = '*****'
last_attempt_id = 0

wcapi = API(
    # Update here your website/domain
    url="https://WWW.YOURWEBSITE.TLD",
    # add here the WooCommerce REST API consumer key
    consumer_key="ck_****************************",
    # then the secret key
    consumer_secret="cs_************************",
    wp_api=True,
    version="wc/v3",
    timeout=20
)

# Getting the current date and time
dt = datetime.now()
ts = datetime.timestamp(dt)

total = 10
page = 0

logger = open('eway-migration-' + str(ts) + '.log', 'w')

with SSHTunnelForwarder(
        (ssh_host, ssh_port),
        ssh_username=ssh_user,
        # your ssh key here
        ssh_password=ssh_password,
        remote_bind_address=(mysql_host, mysql_port)) as tunnel:
    conn = pymysql.connect(host=mysql_host, user=mysql_user,
                           passwd=mysql_pwd, db=mysql_dbname,
                           port=tunnel.local_bind_port)

    mydb = mysql.connector.connect(host=mysql_host, user=mysql_user,
                                   password=mysql_pwd, database=mysql_dbname,
                                   port=tunnel.local_bind_port)

    while total == 10:
        page = page + 1
        # get the list of the users/customers
        customers = wcapi.get("customers?order=asc&orderby=id&role=all&per_page=10&page=" + str(page)).json()
        total = len(customers)

        for customer in customers:
            if customer['id'] < last_attempt_id:
                continue

            for meta in customer['meta_data']:
                if meta['key'] == '_eway_token_cards':
                    # print(meta['value'])

                    for value, index in enumerate(meta['value']):
                        # print('id', meta['value'][index]['id'])
                        # print('number', meta['value'][index]['number'])
                        # print('exp_month', meta['value'][index]['exp_month'])
                        # print('exp_year', meta['value'][index]['exp_year'])

                        if isinstance(meta['value'], list):
                            continue

                        # print('---------------')
                        # print("User ID: " + str(customer['id']))
                        hasCard = False

                        if len(meta['value'][index]) > 0:

                            token_id = ''
                            card_number = ''
                            exp_month = ''
                            exp_year = ''

                            for item, x in enumerate(meta['value'][index]):

                                if x == 'id':
                                    # print('token id', meta['value'][index][x])
                                    token_id = meta['value'][index][x]
                                    hasCard = True
                                elif x == 'number':
                                    # print('number', meta['value'][index][x])
                                    card_number = meta['value'][index][x]
                                    hasCard = True
                                elif x == 'exp_month':
                                    # print('exp_month', meta['value'][index][x])
                                    exp_month = meta['value'][index][x]
                                    hasCard = True
                                elif x == 'exp_year':
                                    # print('exp_year', meta['value'][index][x])
                                    exp_year = meta['value'][index][x]
                                    hasCard = True

                            # in case there is a card
                            if hasCard and token_id != '' and card_number != '' and exp_month != '' and exp_year != '':
                                print('--------------------------------')
                                print("User ID: ", customer['id'])
                                print("eWay Token ID: ", token_id)
                                print("eWay Card Number: ", card_number)
                                print("eWay Expiry Month: ", exp_month)
                                print("eWay Expiry Year: ", exp_year)
                                print('--------------------------------')

                                logger.write('--------------------------------')
                                logger.write("\n")
                                logger.write("User ID: " + str(customer['id']))
                                logger.write("\n")
                                logger.write("eWay Token ID: " + str(token_id))
                                logger.write("\n")
                                logger.write("eWay Card Number: " + str(card_number))
                                logger.write("\n")
                                logger.write("eWay Expiry Month: " + str(exp_month))
                                logger.write("\n")
                                logger.write("eWay Expiry Year: " + str(exp_year))
                                logger.write("\n")
                                logger.write('--------------------------------')
                                logger.write("\n")

                                # check first if we already have the card recorded
                                sql = 'SELECT token_id FROM ' + table_prefix + 'woocommerce_payment_tokens WHERE gateway_id = "eway" AND token = "' + str(
                                    token_id) + '" AND user_id = ' + str(customer['id']) + ' AND type = "Eway_CC"'
                                print(sql)
                                logger.write(sql + "\n")
                                token = pd.read_sql_query(sql, conn)
                                table_token_id = 0

                                if len(token) > 0:
                                    table_token_id = token['token_id'][0]

                                if table_token_id == 0:
                                    # insert the token if not exist
                                    sql = 'INSERT INTO ' + table_prefix + 'woocommerce_payment_tokens ( gateway_id, token, user_id, type, is_default ) VALUES ( "eway", "' + str(
                                        token_id) + '", ' + str(customer['id']) + ', "Eway_CC", 0 );'
                                    print(sql)
                                    logger.write(sql + "\n")
                                    mycursor = mydb.cursor()
                                    mycursor.execute(sql)
                                    mydb.commit()
                                    time.sleep(5)
                                    sql = 'SELECT token_id FROM ' + table_prefix + 'woocommerce_payment_tokens WHERE gateway_id = "eway" AND token = "' + str(
                                        token_id) + '" AND user_id = ' + str(customer['id']) + ' AND type = "Eway_CC"'
                                    token = pd.read_sql_query(sql, conn)
                                    print(sql)
                                    logger.write(sql + "\n")
                                    if len(token) > 0:
                                        table_token_id = token['token_id'][0]

                                if table_token_id != 0:
                                    # search first if the card number exists or not
                                    sql = 'SELECT meta_id FROM ' + table_prefix + 'woocommerce_payment_tokenmeta WHERE payment_token_id = ' + str(
                                        table_token_id) + ' AND meta_key = "number" AND meta_value ="' + card_number + '"'
                                    number_meta_id = pd.read_sql_query(sql, conn)
                                    print(sql)
                                    logger.write(sql + "\n")

                                    # we will only add if no record exists
                                    if len(number_meta_id) == 0:
                                        sql = 'INSERT INTO ' + table_prefix + 'woocommerce_payment_tokenmeta ( payment_token_id, meta_key, meta_value ) VALUES ( ' + str(
                                            table_token_id) + ', "number", "' + card_number + '" )'
                                        mycursor = mydb.cursor()
                                        mycursor.execute(sql)
                                        mydb.commit()
                                        print(sql)
                                        logger.write(sql + "\n")

                                    # search first if the expiry_year exists or not
                                    sql = 'SELECT meta_id FROM ' + table_prefix + 'woocommerce_payment_tokenmeta WHERE payment_token_id = ' + str(
                                        table_token_id) + ' AND meta_key = "expiry_year" AND meta_value ="' + exp_year + '"'
                                    print(sql)
                                    logger.write(sql + "\n")
                                    expiry_year_row = pd.read_sql_query(sql, conn)

                                    # we will only add if no record exists
                                    if len(expiry_year_row) == 0:
                                        sql = 'INSERT INTO ' + table_prefix + 'woocommerce_payment_tokenmeta ( payment_token_id, meta_key, meta_value ) VALUES ( ' + str(
                                            table_token_id) + ', "expiry_year", "' + exp_year + '" )'
                                        mycursor = mydb.cursor()
                                        mycursor.execute(sql)
                                        mydb.commit()
                                        print(sql)
                                        logger.write(sql + "\n")

                                    # search first if the expiry_month exists or not
                                    sql = 'SELECT meta_id FROM ' + table_prefix + 'woocommerce_payment_tokenmeta WHERE payment_token_id = ' + str(
                                        table_token_id) + ' AND meta_key = "expiry_month" AND meta_value ="' + exp_month + '"'
                                    print(sql)
                                    logger.write(sql + "\n")
                                    expiry_month_row = pd.read_sql_query(sql, conn)

                                    # we will only add if no record exists
                                    if len(expiry_month_row) == 0:
                                        sql = 'INSERT INTO ' + table_prefix + 'woocommerce_payment_tokenmeta ( payment_token_id, meta_key, meta_value ) VALUES ( ' + str(
                                            table_token_id) + ', "expiry_month", "' + exp_month + '" )'
                                        mycursor = mydb.cursor()
                                        mycursor.execute(sql)
                                        mydb.commit()
                                        print(sql)
                                        logger.write(sql + "\n")

                            elif not hasCard:

                                for card in meta['value'][index]:

                                    token_id = ''
                                    card_number = ''
                                    exp_month = ''
                                    exp_year = ''

                                    for carditem, y in enumerate(card):
                                        if y == 'id':
                                            # print('token id', card[y])
                                            token_id = card[y]
                                            # hasCard = True
                                        elif y == 'number':
                                            # print('number', card[y])
                                            card_number = card[y]
                                            # hasCard = True
                                        elif y == 'exp_month':
                                            # print('exp_month', card[y])
                                            exp_month = card[y]
                                            # hasCard = True
                                        elif y == 'exp_year':
                                            # print('exp_year', card[y])
                                            exp_year = card[y]
                                            # hasCard = True

                                    if token_id != '' and card_number != '' and exp_month != '' and exp_year != '':

                                        print('--------------------------------')
                                        print("User ID: ", customer['id'])
                                        print("eWay Token ID: ", token_id)
                                        print("eWay Card Number: ", card_number)
                                        print("eWay Expiry Month: ", exp_month)
                                        print("eWay Expiry Year: ", exp_year)
                                        print('--------------------------------')

                                        logger.write('--------------------------------')
                                        logger.write("User ID: " + str(customer['id']))
                                        logger.write("eWay Token ID: " + str(token_id))
                                        logger.write("eWay Card Number: " + str(card_number))
                                        logger.write("eWay Expiry Month: " + str(exp_month))
                                        logger.write("eWay Expiry Year: " + str(exp_year))
                                        logger.write('--------------------------------')

                                        # check first if we already have the card recorded
                                        sql = 'SELECT * FROM ' + table_prefix + 'woocommerce_payment_tokens WHERE gateway_id = "eway" AND token = "' + str(
                                            token_id) + '" AND user_id = ' + str(
                                            customer['id']) + ' AND type = "Eway_CC"'
                                        print(sql)
                                        logger.write(sql + "\n")

                                        # check first if we already have the card recorded
                                        sql = 'SELECT token_id FROM ' + table_prefix + 'woocommerce_payment_tokens WHERE gateway_id = "eway" AND token = "' + str(
                                            token_id) + '" AND user_id = ' + str(
                                            customer['id']) + ' AND type = "Eway_CC"'
                                        token = pd.read_sql_query(sql, conn)
                                        print(sql)
                                        logger.write(sql + "\n")
                                        table_token_id = 0
                                        if len(token) > 0:
                                            table_token_id = token['token_id'][0]

                                        if table_token_id == 0:
                                            # insert the token if not exist
                                            sql = 'INSERT INTO ' + table_prefix + 'woocommerce_payment_tokens ( gateway_id, token, user_id, type, is_default ) VALUES ( "eway", "' + str(
                                                token_id) + '", ' + str(customer['id']) + ', "Eway_CC", 0 );'
                                            mycursor = mydb.cursor()
                                            mycursor.execute(sql)
                                            mydb.commit()
                                            time.sleep(5)
                                            print(sql)
                                            logger.write(sql + "\n")
                                            sql = 'SELECT token_id FROM ' + table_prefix + 'woocommerce_payment_tokens WHERE gateway_id = "eway" AND token = "' + str(
                                                token_id) + '" AND user_id = ' + str(
                                                customer['id']) + ' AND type = "Eway_CC"'
                                            token = pd.read_sql_query(sql, conn)
                                            print(sql)
                                            logger.write(sql + "\n")
                                            if len(token) > 0:
                                                table_token_id = token['token_id'][0]

                                        if table_token_id != 0:
                                            # search first if the card number exists or not
                                            sql = 'SELECT meta_id FROM ' + table_prefix + 'woocommerce_payment_tokenmeta WHERE payment_token_id = ' + str(
                                                table_token_id) + ' AND meta_key = "number" AND meta_value ="' + card_number + '"'
                                            number_meta_id = pd.read_sql_query(sql, conn)
                                            print(sql)
                                            logger.write(sql + "\n")

                                            # we will only add if no record exists
                                            if len(number_meta_id) == 0:
                                                sql = 'INSERT INTO ' + table_prefix + 'woocommerce_payment_tokenmeta ( payment_token_id, meta_key, meta_value ) VALUES ( ' + str(
                                                    table_token_id) + ', "number", "' + card_number + '" )'
                                                mycursor = mydb.cursor()
                                                mycursor.execute(sql)
                                                mydb.commit()
                                                print(sql)
                                                logger.write(sql + "\n")

                                            # search first if the expiry_year exists or not
                                            sql = 'SELECT meta_id FROM ' + table_prefix + 'woocommerce_payment_tokenmeta WHERE payment_token_id = ' + str(
                                                table_token_id) + ' AND meta_key = "expiry_year" AND meta_value ="' + exp_year + '"'
                                            print(sql)
                                            logger.write(sql + "\n")
                                            expiry_year_row = pd.read_sql_query(sql, conn)

                                            # we will only add if no record exists
                                            if len(expiry_year_row) == 0:
                                                sql = 'INSERT INTO ' + table_prefix + 'woocommerce_payment_tokenmeta ( payment_token_id, meta_key, meta_value ) VALUES ( ' + str(
                                                    table_token_id) + ', "expiry_year", "' + exp_year + '" )'
                                                mycursor = mydb.cursor()
                                                mycursor.execute(sql)
                                                mydb.commit()
                                                print(sql)
                                                logger.write(sql + "\n")

                                            # search first if the expiry_month exists or not
                                            sql = 'SELECT meta_id FROM ' + table_prefix + 'woocommerce_payment_tokenmeta WHERE payment_token_id = ' + str(
                                                table_token_id) + ' AND meta_key = "expiry_month" AND meta_value ="' + exp_month + '"'
                                            # print(sql)
                                            expiry_month_row = pd.read_sql_query(sql, conn)

                                            # we will only add if no record exists
                                            if len(expiry_month_row) == 0:
                                                sql = 'INSERT INTO ' + table_prefix + 'woocommerce_payment_tokenmeta ( payment_token_id, meta_key, meta_value ) VALUES ( ' + str(
                                                    table_token_id) + ', "expiry_month", "' + exp_month + '" )'
                                                mycursor = mydb.cursor()
                                                mycursor.execute(sql)
                                                mydb.commit()
                                                print(sql)
                                                logger.write(sql + "\n")


conn.close()
logger.close()