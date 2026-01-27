from users.sql_users import create_users_table
from posts.sql_posts import init_posts_table
from comments.sql_comments import init_comments_table
from profile.sql_profile import create_profile_table_and_functions

def init_all_tables():
    create_users_table()
    init_posts_table()
    init_comments_table()
    create_profile_table_and_functions()
