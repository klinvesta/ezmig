-- ezmig:apply
create table users (
   name varchar2(100) not null
);

-- ezmig:rollback
drop table users;
