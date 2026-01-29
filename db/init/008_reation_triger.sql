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

-- триггер на таблицу reactions
DROP TRIGGER IF EXISTS trg_validate_reaction ON reactions;

CREATE TRIGGER trg_validate_reaction
BEFORE INSERT OR UPDATE ON reactions
FOR EACH ROW
EXECUTE FUNCTION validate_reaction_fk();
