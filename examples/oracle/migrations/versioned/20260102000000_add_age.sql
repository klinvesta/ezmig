-- ezmig:apply
alter table users add (
   age number
);

-- ezmig:rollback
alter table users drop column age;
