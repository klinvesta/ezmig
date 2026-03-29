-- ezmig:apply
create table users (
   name text not null
);

-- ezmig:rollback
drop table users;
