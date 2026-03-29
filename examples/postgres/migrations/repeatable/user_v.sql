drop view if exists users_v;

create view users_v as
   select name,
          age
     from users
    where 1 = 1;
