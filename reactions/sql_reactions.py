from django.db import connection

# =========================
# Utils
# =========================

def dict_fetchone(cursor):
    row = cursor.fetchone()
    if row is None:
        return None
    desc = cursor.description
    return {desc[i].name: row[i] for i in range(len(row))}

def dict_fetchall(cursor):
    rows = cursor.fetchall()
    desc = cursor.description
    return [
        {desc[i].name: row[i] for i in range(len(row))}
        for row in rows
    ]

# =========================
# Init reactions table + SQL logic
# =========================

def init_reactions_table():
    with connection.cursor() as cursor:
        # -------------------------
        # REACTIONS TABLE
        # -------------------------
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS reactions (
            id SERIAL PRIMARY KEY,
            user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            reactable_type VARCHAR(20) NOT NULL CHECK (reactable_type IN ('post', 'comment')),
            reactable_id INT NOT NULL CHECK (reactable_id > 0),
            reaction_type VARCHAR(20) NOT NULL CHECK (reaction_type IN ('like', 'love', 'dislike')),
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, reactable_type, reactable_id)
        );
        """)

        # -------------------------
        # REPUTATION UPDATE TRIGGER (УЛУЧШЕННАЯ ВЕРСИЯ)
        # -------------------------
        cursor.execute("""
        CREATE OR REPLACE FUNCTION update_reputation_on_reaction()
        RETURNS TRIGGER AS $$
        DECLARE
            owner_id INT;
            old_reputation_change INT := 0;
            new_reputation_change INT := 0;
            total_change INT := 0;
            current_reputation INT;
        BEGIN
            RAISE NOTICE '========================================';
            RAISE NOTICE 'TRIGGER FIRED: % operation', TG_OP;
            
            -- Определяем владельца контента
            IF COALESCE(NEW.reactable_type, OLD.reactable_type) = 'post' THEN
                SELECT author_id INTO owner_id 
                FROM posts 
                WHERE id = COALESCE(NEW.reactable_id, OLD.reactable_id);
                RAISE NOTICE 'Post owner_id: %', owner_id;
            ELSIF COALESCE(NEW.reactable_type, OLD.reactable_type) = 'comment' THEN
                SELECT user_id INTO owner_id 
                FROM comments 
                WHERE id = COALESCE(NEW.reactable_id, OLD.reactable_id);
                RAISE NOTICE 'Comment owner_id: %', owner_id;
            END IF;

            -- Проверяем, найден ли владелец
            IF owner_id IS NULL THEN
                RAISE NOTICE 'WARNING: owner_id is NULL - content not found!';
                IF TG_OP = 'DELETE' THEN
                    RETURN OLD;
                ELSE
                    RETURN NEW;
                END IF;
            END IF;

            -- Не даем самому себе менять репутацию
            IF owner_id = COALESCE(NEW.user_id, OLD.user_id) THEN
                RAISE NOTICE 'User % trying to react to own content - skipping reputation change', owner_id;
                IF TG_OP = 'DELETE' THEN
                    RETURN OLD;
                ELSE
                    RETURN NEW;
                END IF;
            END IF;

            -- Получаем текущую репутацию
            SELECT reputation INTO current_reputation FROM profile WHERE user_id = owner_id;
            RAISE NOTICE 'Current reputation of user %: %', owner_id, current_reputation;

            -- INSERT: добавляем репутацию
            IF TG_OP = 'INSERT' THEN
                new_reputation_change := CASE 
                    WHEN NEW.reaction_type = 'like' THEN 1
                    WHEN NEW.reaction_type = 'love' THEN 2
                    WHEN NEW.reaction_type = 'dislike' THEN -1
                    ELSE 0
                END;
                
                RAISE NOTICE 'INSERT: user_id=%, reactable_type=%, reactable_id=%, reaction=%', 
                    NEW.user_id, NEW.reactable_type, NEW.reactable_id, NEW.reaction_type;
                RAISE NOTICE 'INSERT: Adding % reputation to user %', new_reputation_change, owner_id;
                
                UPDATE profile 
                SET reputation = reputation + new_reputation_change 
                WHERE user_id = owner_id;
                
                SELECT reputation INTO current_reputation FROM profile WHERE user_id = owner_id;
                RAISE NOTICE 'New reputation after INSERT: %', current_reputation;
                
            -- DELETE: убираем репутацию
            ELSIF TG_OP = 'DELETE' THEN
                old_reputation_change := CASE 
                    WHEN OLD.reaction_type = 'like' THEN -1
                    WHEN OLD.reaction_type = 'love' THEN -2
                    WHEN OLD.reaction_type = 'dislike' THEN 1
                    ELSE 0
                END;
                
                RAISE NOTICE 'DELETE: user_id=%, reactable_type=%, reactable_id=%, reaction=%', 
                    OLD.user_id, OLD.reactable_type, OLD.reactable_id, OLD.reaction_type;
                RAISE NOTICE 'DELETE: Changing reputation by % for user %', old_reputation_change, owner_id;
                
                UPDATE profile 
                SET reputation = reputation + old_reputation_change 
                WHERE user_id = owner_id;
                
                SELECT reputation INTO current_reputation FROM profile WHERE user_id = owner_id;
                RAISE NOTICE 'New reputation after DELETE: %', current_reputation;
                
            -- UPDATE: отменяем старую и добавляем новую
            ELSIF TG_OP = 'UPDATE' THEN
                -- Отменяем старую реакцию
                old_reputation_change := CASE 
                    WHEN OLD.reaction_type = 'like' THEN -1
                    WHEN OLD.reaction_type = 'love' THEN -2
                    WHEN OLD.reaction_type = 'dislike' THEN 1
                    ELSE 0
                END;
                
                -- Добавляем новую реакцию
                new_reputation_change := CASE 
                    WHEN NEW.reaction_type = 'like' THEN 1
                    WHEN NEW.reaction_type = 'love' THEN 2
                    WHEN NEW.reaction_type = 'dislike' THEN -1
                    ELSE 0
                END;
                
                total_change := old_reputation_change + new_reputation_change;
                
                RAISE NOTICE 'UPDATE: user_id=%, reactable_type=%, reactable_id=%', 
                    NEW.user_id, NEW.reactable_type, NEW.reactable_id;
                RAISE NOTICE 'UPDATE: Changing from % to % for user %, total change: %', 
                    OLD.reaction_type, NEW.reaction_type, owner_id, total_change;
                
                -- Применяем изменение
                UPDATE profile 
                SET reputation = reputation + total_change
                WHERE user_id = owner_id;
                
                SELECT reputation INTO current_reputation FROM profile WHERE user_id = owner_id;
                RAISE NOTICE 'New reputation after UPDATE: %', current_reputation;
            END IF;

            RAISE NOTICE '========================================';

            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            ELSE
                RETURN NEW;
            END IF;
        END;
        $$ LANGUAGE plpgsql;
        """)

        cursor.execute("""
        DROP TRIGGER IF EXISTS trigger_update_reputation ON reactions;
        CREATE TRIGGER trigger_update_reputation
        AFTER INSERT OR UPDATE OR DELETE ON reactions
        FOR EACH ROW
        EXECUTE FUNCTION update_reputation_on_reaction();
        """)

        # -------------------------
        # FOREIGN KEY VALIDATION
        # -------------------------
        cursor.execute("""
        CREATE OR REPLACE FUNCTION validate_reaction_fk()
        RETURNS TRIGGER AS $$
        BEGIN
            IF (NEW.reactable_type = 'post') THEN
                PERFORM 1 FROM posts WHERE id = NEW.reactable_id;
                IF NOT FOUND THEN
                    RAISE EXCEPTION 'Post id % does not exist', NEW.reactable_id;
                END IF;
            ELSIF (NEW.reactable_type = 'comment') THEN
                PERFORM 1 FROM comments WHERE id = NEW.reactable_id;
                IF NOT FOUND THEN
                    RAISE EXCEPTION 'Comment id % does not exist', NEW.reactable_id;
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """)

        cursor.execute("""
        DROP TRIGGER IF EXISTS trg_validate_reaction ON reactions;
        CREATE TRIGGER trg_validate_reaction
        BEFORE INSERT ON reactions
        FOR EACH ROW
        EXECUTE FUNCTION validate_reaction_fk();
        """)

        # -------------------------
        # INDEXES
        # -------------------------
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_reactions_post 
        ON reactions(reactable_type, reactable_id) 
        WHERE reactable_type = 'post';
        """)
        
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_reactions_comment 
        ON reactions(reactable_type, reactable_id) 
        WHERE reactable_type = 'comment';
        """)

        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_reactions_user 
        ON reactions(user_id);
        """)

        # =========================
        # ADD OR UPDATE REACTION
        # =========================
        cursor.execute("DROP FUNCTION IF EXISTS add_or_update_reaction_func(INT, VARCHAR, INT, VARCHAR)")
        cursor.execute("""
        CREATE FUNCTION add_or_update_reaction_func(
            p_user_id INT,
            p_reactable_type VARCHAR,
            p_reactable_id INT,
            p_reaction_type VARCHAR
        )
        RETURNS TABLE(r_id INT, r_user_id INT, r_reactable_type VARCHAR, r_reactable_id INT, r_reaction_type VARCHAR) AS $$
        BEGIN
            RAISE NOTICE 'add_or_update_reaction_func called: user_id=%, type=%, id=%, reaction=%', 
                p_user_id, p_reactable_type, p_reactable_id, p_reaction_type;
            
            RETURN QUERY
            INSERT INTO reactions(user_id, reactable_type, reactable_id, reaction_type, created_at)
            VALUES (p_user_id, p_reactable_type, p_reactable_id, p_reaction_type, NOW())
            ON CONFLICT (user_id, reactable_type, reactable_id) 
            DO UPDATE SET reaction_type = EXCLUDED.reaction_type, created_at = NOW()
            RETURNING reactions.id, reactions.user_id, reactions.reactable_type, reactions.reactable_id, reactions.reaction_type;
        END;
        $$ LANGUAGE plpgsql;
        """)

        # =========================
        # REMOVE REACTION
        # =========================
        cursor.execute("DROP FUNCTION IF EXISTS remove_reaction_func(INT, VARCHAR, INT)")
        cursor.execute("""
        CREATE FUNCTION remove_reaction_func(
            p_user_id INT,
            p_reactable_type VARCHAR,
            p_reactable_id INT
        )
        RETURNS BOOLEAN AS $$
        DECLARE
            deleted BOOLEAN := FALSE;
        BEGIN
            RAISE NOTICE 'remove_reaction_func called: user_id=%, type=%, id=%', 
                p_user_id, p_reactable_type, p_reactable_id;
            
            DELETE FROM reactions 
            WHERE user_id = p_user_id 
              AND reactable_type = p_reactable_type 
              AND reactable_id = p_reactable_id;
            
            IF FOUND THEN
                deleted := TRUE;
                RAISE NOTICE 'Reaction deleted successfully';
            ELSE
                RAISE NOTICE 'No reaction found to delete';
            END IF;
            
            RETURN deleted;
        END;
        $$ LANGUAGE plpgsql;
        """)

        # =========================
        # GET REACTIONS STATS FOR POST
        # =========================
        cursor.execute("DROP FUNCTION IF EXISTS get_post_reactions_stats_func(INT)")
        cursor.execute("""
        CREATE FUNCTION get_post_reactions_stats_func(p_post_id INT)
        RETURNS TABLE(reaction_type VARCHAR, count BIGINT) AS $$
        BEGIN
            RETURN QUERY
            SELECT r.reaction_type, COUNT(*) as count
            FROM reactions r
            WHERE r.reactable_type = 'post' AND r.reactable_id = p_post_id
            GROUP BY r.reaction_type;
        END;
        $$ LANGUAGE plpgsql;
        """)

        # =========================
        # GET REACTIONS STATS FOR COMMENT
        # =========================
        cursor.execute("DROP FUNCTION IF EXISTS get_comment_reactions_stats_func(INT)")
        cursor.execute("""
        CREATE FUNCTION get_comment_reactions_stats_func(p_comment_id INT)
        RETURNS TABLE(reaction_type VARCHAR, count BIGINT) AS $$
        BEGIN
            RETURN QUERY
            SELECT r.reaction_type, COUNT(*) as count
            FROM reactions r
            WHERE r.reactable_type = 'comment' AND r.reactable_id = p_comment_id
            GROUP BY r.reaction_type;
        END;
        $$ LANGUAGE plpgsql;
        """)

        # =========================
        # GET USER REACTION ON POST
        # =========================
        cursor.execute("DROP FUNCTION IF EXISTS get_user_reaction_on_post_func(INT, INT)")
        cursor.execute("""
        CREATE FUNCTION get_user_reaction_on_post_func(p_user_id INT, p_post_id INT)
        RETURNS VARCHAR AS $$
        DECLARE
            reaction VARCHAR;
        BEGIN
            SELECT reaction_type INTO reaction
            FROM reactions
            WHERE user_id = p_user_id 
              AND reactable_type = 'post' 
              AND reactable_id = p_post_id;
            
            RETURN reaction;
        END;
        $$ LANGUAGE plpgsql;
        """)

        # =========================
        # GET USER REACTION ON COMMENT
        # =========================
        cursor.execute("DROP FUNCTION IF EXISTS get_user_reaction_on_comment_func(INT, INT)")
        cursor.execute("""
        CREATE FUNCTION get_user_reaction_on_comment_func(p_user_id INT, p_comment_id INT)
        RETURNS VARCHAR AS $$
        DECLARE
            reaction VARCHAR;
        BEGIN
            SELECT reaction_type INTO reaction
            FROM reactions
            WHERE user_id = p_user_id 
              AND reactable_type = 'comment' 
              AND reactable_id = p_comment_id;
            
            RETURN reaction;
        END;
        $$ LANGUAGE plpgsql;
        """)

        # =========================
        # GET POSTS WITH REACTIONS
        # =========================
        cursor.execute("DROP FUNCTION IF EXISTS get_posts_with_reactions_func()")
        cursor.execute("""
        CREATE FUNCTION get_posts_with_reactions_func()
        RETURNS TABLE(
            id INT,
            title VARCHAR,
            content TEXT,
            author_id INT,
            created_at TIMESTAMP,
            likes_count BIGINT,
            loves_count BIGINT,
            dislikes_count BIGINT
        ) AS $$
        BEGIN
            RETURN QUERY
            SELECT 
                p.id,
                p.title,
                p.content,
                p.author_id,
                p.created_at,
                COUNT(CASE WHEN r.reaction_type = 'like' THEN 1 END) as likes_count,
                COUNT(CASE WHEN r.reaction_type = 'love' THEN 1 END) as loves_count,
                COUNT(CASE WHEN r.reaction_type = 'dislike' THEN 1 END) as dislikes_count
            FROM posts p
            LEFT JOIN reactions r ON r.reactable_type = 'post' AND r.reactable_id = p.id
            GROUP BY p.id, p.title, p.content, p.author_id, p.created_at
            ORDER BY p.created_at DESC;
        END;
        $$ LANGUAGE plpgsql;
        """)

    connection.commit()
    print("✔ reactions table + SQL functions initialized")

# =========================
# Python wrappers
# =========================

def add_or_update_reaction(user_id, reactable_type, reactable_id, reaction_type):
    """Добавить или обновить реакцию"""
    print(f"[Python] add_or_update_reaction: user_id={user_id}, type={reactable_type}, id={reactable_id}, reaction={reaction_type}")
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM add_or_update_reaction_func(%s, %s, %s, %s)",
            (user_id, reactable_type, reactable_id, reaction_type)
        )
        result = dict_fetchone(cursor)
    connection.commit()
    print(f"[Python] Result: {result}")
    return result


def remove_reaction(user_id, reactable_type, reactable_id):
    """Удалить реакцию"""
    print(f"[Python] remove_reaction: user_id={user_id}, type={reactable_type}, id={reactable_id}")
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT remove_reaction_func(%s, %s, %s)",
            (user_id, reactable_type, reactable_id)
        )
        result = cursor.fetchone()[0]
    connection.commit()
    print(f"[Python] Deleted: {result}")
    return result


def get_post_reactions_stats(post_id):
    """Получить статистику реакций для поста"""
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM get_post_reactions_stats_func(%s)", (post_id,))
        return dict_fetchall(cursor)


def get_comment_reactions_stats(comment_id):
    """Получить статистику реакций для комментария"""
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM get_comment_reactions_stats_func(%s)", (comment_id,))
        return dict_fetchall(cursor)


def get_user_reaction_on_post(user_id, post_id):
    """Получить реакцию пользователя на пост"""
    with connection.cursor() as cursor:
        cursor.execute("SELECT get_user_reaction_on_post_func(%s, %s)", (user_id, post_id))
        result = cursor.fetchone()
        return result[0] if result else None


def get_user_reaction_on_comment(user_id, comment_id):
    """Получить реакцию пользователя на комментарий"""
    with connection.cursor() as cursor:
        cursor.execute("SELECT get_user_reaction_on_comment_func(%s, %s)", (user_id, comment_id))
        result = cursor.fetchone()
        return result[0] if result else None


def get_posts_with_reactions():
    """Получить все посты с количеством реакций"""
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM get_posts_with_reactions_func()")
        return dict_fetchall(cursor)