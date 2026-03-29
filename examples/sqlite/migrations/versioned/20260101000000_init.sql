-- ezmig:apply
create table users (name text);

-- ezmig:rollback
drop table users;
