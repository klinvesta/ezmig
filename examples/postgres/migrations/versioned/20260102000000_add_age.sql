-- ezmig:apply
ALTER TABLE users ADD COLUMN age INTEGER;

-- ezmig:rollback
ALTER TABLE users DROP COLUMN age;
