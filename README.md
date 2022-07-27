Requirements:
* Wordpress 
* WooCommerce 
* eWay by WooCommerce -https://woocommerce.com/products/eway/
* Python 3 / Pip
* Database Access

Note: You can only use this if the old way you have is storing the payment tokens via usermeta instead of the payment tokens table.

Steps:
1. Ensure that you are using the eWay version at least 3.4.x
2. After cloning this, you need to install the modules
3. `pip install woocommerce` or `pip3 install woocommerce`
4. `pip install pymysql` or `pip3 install pymysql`
5. `pip install pandas` or `pip3 install pandas`
6. `pip install SSHTunnelForwarder` or `pip3 install SSHTunnelForwarder`
7. `pip install mysql.connector` or `pip3 install mysql.connector`
8. `pip install datetime` or `pip3 install datetime`
9. `pip install time` or `pip3 install time`
10. Generate WooCommerce REST API Consumer and Secret Keys (if not yet created)
11. Update the `table_prefix`, `ssh_host`, `ssh_port`, `ssh_user`, `ssh_password`, `mysql_host`, `mysql_port`, `mysql_user`, `mysql_dbname`, `mysql_pwd`
12. Also, inside the `wcapi`, update its `url`, `consumer_key`, and `consumer_secret`
13. In case that the script time outs, check on the logs and update the `last_attempt_id` to the last id processed before the error happened
14. Check the payment token meta if details were, if not you may need to run this script again
15. Run this script after once everything were inserted on the payment tokens ang payment token meta tables. (Note the you have to update the `wp_` to what is the wordpress database table prefix on your end) ```DELETE FROM `wp_usermeta` WHERE `meta_key` = '_eway_token_cards';```