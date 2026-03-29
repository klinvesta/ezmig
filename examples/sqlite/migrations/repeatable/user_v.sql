DROP VIEW IF EXISTS users_v;

CREATE VIEW users_v AS
    SELECT name,
            age
    FROM users
    WHERE 1 = 1;
