-- ezmig:apply
alter table users add COLUMN age integer;

-- ezmig:rollback
alter table users drop COLUMN age;
