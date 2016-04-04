sqlibrist
=========

Sqlibrist is command-line tool, made for developers, who do not use ORM to manage their database
structure. Programming database objects and deploying them to production
is not easy. Naive approach is to manually write patches with SQL statements and then replay
them on others DB instances. This, being simple and straightforward, may get tricky
when your database structure grows in size and have numerous inter-dependent
objects.

Sqlibrist in essense is tool to make the process of creating SQL patches much more
easy, and as side-effect it proposes a way to organize your SQL code. It does not
dictate design desisions, or stands on your way when you do something wrong
(notorious shooting in foot). All database objects are described declaratively
in separate files in the form of ``CREATE TABLE`` or ``CREATE FUNCTION``, having
dependency instructions.

You may think of sqlibrist as Version Control System for database. The whole thing
is inspired by Sqitch (see Alternatives below) and Django Migrations (may be you
remember Django South). Every time you invoke ``makemigration`` command, snapshot
of current scheme is made and compared with previous snapshot. Then, SQL patch
is created with instructions to recreate all changed objects cascadely with their
dependencies, create new or remove deleted. In the latter case, sqlibrist will not
let you delete object that has left dependants.

Currently PostgreSQL is supported. MySQL support is experimental, and not well-tested
yet.


Platform compatibility
======================

Linux, Mac OS, Windows. See installation instructions for each below.


Requirements
============

Python dependencies:

- PyYAML
- psycopg2 (optional)
- mysql-python (optional)

Installation
============

Linux
-----

**Ubuntu/Debian**

First install required libraries::

    $ sudo apt-get install python-pip python-dev libyaml-dev
    $ sudo apt-get install libmysqlclient-dev  # for MySQL
    $ sudo apt-get install libpq-dev  # PostgreSQL

Sqlibrist can be installed into virtualenv::

    $ pip install sqlibrist

or system-wide::

    $ sudo pip install sqlibrist

**Fedora/CentOS/RHEL**

First install required libraries (replace ``dnf`` to ``yum`` if you are using
pre-dnf package manager)::

    $ sudo dnf install python-devel python-pip libyaml-devel
    $ sudo dnf install postgresql-devel  # PostgreSQL

    $ sudo dnf install mariadb-devel  # for MariaDB
    or
    $ sudo dnf install mysql++-devel  # for MySQL

Sqlibrist can be installed into virtualenv::

    $ pip install sqlibrist

or system-wide::

    $ sudo pip install sqlibrist


MacOS
-----
TODO

Windows
-------
TODO

Tutorial
========

Let's create simple project and go through typical steps of DB schema manageent.
This will be small webshop.

Create empty directory::

    $ mkdir shop_schema
    $ cd shop_schema

Then we need to create sqlibrist database structure, where we will keep
schema and migrations::

    $ sqlibrist init
    Creating directories...
    Done.

You will get the following DB structure::

    shop_schema
        sqlibrist.yaml
        migrations
        schema
            constraints
            functions
            indexes
            tables
            triggers
            types
            views

In ``sqlibrist.yaml`` you will configure DB connections::

    ---
    default:
      engine: pg
      user: <username>
      name: <database_name>
      password: <password>
    # host: 127.0.0.1
    # port: 5432

``host`` and ``port`` are optional.

Once you configured DB connection, test if is correct::

    $ sqlibrist test_connection
    Connection OK

Next we need to create sqlibrist migrations table::

    $ sqlibrist initdb
    Creating db...
    Creating schema and migrations log table...

    Done.

Now we are ready to build our DB schema.

Create file ``shop_schema/schema/tables/user.sql``::

    --UP
    CREATE TABLE "user" (
    id SERIAL PRIMARY KEY,
    name TEXT,
    password TEXT);

The first line ``--UP`` means that the following are SQL statements for 'forward'
migration. The opposite is optional ``--DOWN``, which contains instructions for reverting.
To be safe, and not accidentally drop any table with your data, we will not include
anything like DROP TABLE. Working with table upgrades and ``--DOWN`` is on the way
below.

``shop_schema/schema/tables/product.sql``::

    --UP
    CREATE TABLE product (
    id SERIAL PRIMARY KEY,
    name TEXT,
    price MONEY);

``shop_schema/schema/tables/order.sql``::

    --REQ tables/user
    --UP
    CREATE TABLE "order" (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES "user"(id),
    date DATE);

Important here is the ``--REQ tables/user`` statement. It tells sqlibrist, that
``order`` table depends on ``user`` table. This will guarantee, that ``user`` will
be created before ``order``.

``shop_schema/schema/tables/order_product.sql``::

    --REQ tables/order
    --UP
    CREATE TABLE order_product (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES "order"(id),
    product_id INTEGER REFERENCES product(id),
    quantity INTEGER);

Ok, now let's create our first migration::

    $ sqlibrist makemigration -n 'initial'
    Creating:
     tables/user
     tables/product
     tables/order
     tables/order_product
    Creating new migration 0001-initial

New files were created in ``shop_schema/migrations/0001-initial``::

    up.sql
    down.sql
    schema.json

``up.sql`` contains SQL to apply your changes (create tables), ``down.sql`` has nothing
notable, since our .sql files have no ``--DOWN`` section, and the ``schema.json``
has snapshot of current schema.

If you want to make more changes to the schema files prior to applying newly created
migration, delete the directory with those 3 files, in our case ``0001-initial``.

You are free to review and edit ``up.sql`` and ``down.sql``, of course if you know what
you are doing. **DO NOT edit schema.json**.

Now go ahead and apply our migration::

    $ sqlibrist migrate
    Applying migration 0001-initial... done

Well done! Tables are created, but let's do something more interesting.

We will create view that shows all user orders with order total:

``shop_schema/schema/views/user_orders.sql``::

    --REQ tables/user
    --REQ tables/order
    --REQ tables/product
    --REQ tables/order_product

    --UP
    CREATE VIEW user_orders AS SELECT
     u.id as user_id,
     o.id as order_id,
     o.date,
     SUM(p.price*op.quantity) AS total

     FROM "user" u
     INNER JOIN "order" o ON u.id=o.user_id
     INNER JOIN order_product op ON o.id=op.order_id
     INNER JOIN product p ON p.id=op.product_id

     GROUP BY o.id, u.id;

    --DOWN
    DROP VIEW user_orders;

... and function to return only given user's orders:

``shop_schema/schema/functions/get_user_orders.sql``::

    --REQ views/user_orders

    --UP
    CREATE FUNCTION get_user_orders(_user_id INTEGER)
    RETURNS SETOF user_orders
    LANGUAGE SQL AS $$

    SELECT * FROM user_orders
    WHERE user_id=_user_id;

    $$;

    --DOWN
    DROP FUNCTION get_user_orders(INTEGER);

Next create new migration and apply it::

    $ sqlibrist makemigration -n 'user_orders view and function'
    Creating:
     views/user_orders
     functions/get_user_orders
    Creating new migration 0002-user_orders view and function

    $ sqlibrist migrate
    Applying migration 0002-user_orders view and function... done

We have four tables, one view and one function.

Now you want to add one more field in the ``user_orders`` view. There can be couple
of issues here:

* we could try to drop and create updated view, but the database server will
  complain, that *get_user_orders* function depends on droppable view;

* we could be smart and create view with ``CREATE OR REPLACE VIEW user_orders...``,
  however single view's fields and their types make separate type, and the
  function ``get_user_orders`` returns that type. We can't simply change view type
  without recreating the function.

This is where sqlibrist comes to help. Add one more field ``SUM(op.quantity) as order_total``
to the ``user_orders`` view::

    --REQ tables/user
    --REQ tables/order
    --REQ tables/product
    --REQ tables/order_product

    --UP
    CREATE VIEW user_orders AS SELECT
     u.id as user_id,
     o.id as order_id,
     o.date,
     SUM(p.price*op.quantity) AS total,
     SUM(op.quantity) as order_total

     FROM "user" u
     INNER JOIN "order" o ON u.id=o.user_id
     INNER JOIN order_product op ON o.id=op.order_id
     INNER JOIN product p ON p.id=op.product_id

     GROUP BY o.id, u.id;

    --DOWN
    DROP VIEW user_orders;

We can see, what was changed from the latest schema snapshot::

    $ sqlibrist -V diff
    Changed items:
      views/user_orders
    ---

    +++

    @@ -2,7 +2,8 @@

          u.id as user_id,
          o.id as order_id,
          o.date,
    -     SUM(p.price*op.quantity) AS total
    +     SUM(p.price*op.quantity) AS total,
    +     SUM(op.quantity) as total_quantity

          FROM "user" u
          INNER JOIN "order" o ON u.id=o.user_id

Now let's make migration::

    $ sqlibrist makemigration
    Updating:
     dropping:
      functions/get_user_orders
      views/user_orders
     creating:
      views/user_orders
      functions/get_user_orders
    Creating new migration 0003-auto

You can see, that sqlibrist first drops ``get_user_orders`` function, after that
``user_orders`` view does not have dependent objects and can be dropped too.
Then view and function are created in order, opposite to dropping.
Apply our changes::

    $ sqlibrist migrate
    Applying migration 0003-auto... done

Last topic is to make change to table structure. Since we did not add ``--DROP`` section
to our tables, any change has to be made manually. This is done in several steps:

1. Edit CREATE TABLE definition to reflect new structure;
2. Generate new migration with ``makemigration`` command;
3. Manually edit new migration's ``up.sql`` with ALTER TABLE instructions.

To demonstrate this, let's add field ``type text`` to the ``product`` table. It will
look like this:

``shop_schema/schema/tables/product.sql``::

    --UP
    CREATE TABLE product (
    id SERIAL PRIMARY KEY,
    name TEXT,
    "type" TEXT,
    price MONEY);

This was #1. Next create new migration::

    $ sqlibrist makemigration -n 'new product field'
    Updating:
     dropping:
      functions/get_user_orders
      views/user_orders
     creating:
      views/user_orders
      functions/get_user_orders
    Creating new migration 0004-new product field

Please, pay attention here, that even though we changed product table definition,
``tables/product`` is not in migration process, but ALL dependent objects are recreated.
This behavior is intended. This was #2.

Now #3: open ``shop_schema/migrations/0004-new product field/up.sql`` with your editor
and look for line 12 with text ``-- ==== Add your instruction here ====``. This is
the point in migration when all dependent objects are dropped and you can issue
ALTER TABLE instructions.

Just below this line paste following::

    ALTER TABLE product
    ADD COLUMN "type" TEXT;

Your ``up.sql`` will look like this::

    -- begin --
    DROP FUNCTION get_user_orders(INTEGER);
    -- end --


    -- begin --
    DROP VIEW user_orders;
    -- end --


    -- begin --
    -- ==== Add your instruction here ====
    ALTER TABLE product
    ADD COLUMN "type" TEXT;
    -- end --


    -- begin --
    CREATE VIEW user_orders AS SELECT
         u.id as user_id,
         o.id as order_id,
         o.date,
         SUM(p.price*op.quantity) AS total,
         SUM(op.quantity) as total_quantity

         FROM "user" u
         INNER JOIN "order" o ON u.id=o.user_id
         INNER JOIN order_product op ON o.id=op.order_id
         INNER JOIN product p ON p.id=op.product_id

         GROUP BY o.id, u.id;
    -- end --


    -- begin --
    CREATE FUNCTION get_user_orders(_user_id INTEGER)
        RETURNS SETOF user_orders
        LANGUAGE SQL AS $$

        SELECT * FROM user_orders
        WHERE user_id=_user_id;

        $$;
    -- end --

Migration text is self-explanatory: drop function and view, alter table and then
create view and function, with respect to their dependencies.

Finally, apply your changes::

    $ sqlibrist migrate
    Applying migration 0004-new product field... done


Rules of thumb
==============

* **do not add CASCADE to DROP statements, even when dropping views/functions/indexes**.
You may and will implicitly drop table(s) with your data;

* **avoid circular dependencies**. If you create objects that depend on each other
in circle, sqlibrist will not know, how to update them. I bet, you will try to
do so, but migration will not be created and sqlibrist will show you warning and
dependency path;

* **do not create --DOWN sections for tables**. Manually write ALTER TABLE instructions
as described in the Tutorial;

* **always test migrations on your test database before applying them to production**.


Django integration
==================

Sqlibrist has a very small application to integrate itself into your Django
project and access DB configuration.

Installation
------------

Add ``'django_sqlibrist'`` to INSTALLED_APPS

Settings
--------

``SQLIBRIST_DIRECTORY`` - Path to the directory with schema and migrations files.
Defaults to project's BASE_DIR/sql

Usage
-----
::

    $ python manage.py sqlibrist <command> [options]

If you want your tables to be accessible from Django ORM and/or for using
Django Admin for these tables, add following attributes to the model's ``Meta`` class:
::

    class SomeTable(models.Model):
        field1 = models.CharField()
        ...
        class Meta:
            managed = False  # will tell Django to not create migrations for that table
            table_name = 'sometable'  # name of your table

If primary key has other name than ``id`` and type not Integer, add that field to
model class with ``primary_key=True`` argument, for example::

    my_key = models.IntegerField(primary_key=True)

Migrating existing models
-------------------------
TODO:


Alternatives
============

Sqlibrist is not new concept, it has a lot of alternatives, most notable, I think,
is [sqitch](http://sqitch.org/). It is great tool, with rich development history and
community arount it. I started using it at first, however it did not make me completely
happy. My problem with sqitch was pretty hard installation progress
(shame on me, first of all). It is written in Perl and has huge number of dependencies.
For man, unfamiliar with Perl pachage systems, it was quite a challenge to
install sqitch on 3 different Linux distributions: Fedora, Ubuntu and Arch.
In addition, I found sqitch's dependency tracking being complicated and unobvious
to perform relatively simple schema changes. Don't get me wrong - I am not
advocating you against using sqitch, you should try it yourself.


TODO
====

- documentation
    * django_sqlibrist: Migrating existing models
    * detailed info on all commands

Changelog
=========

 0.1.5 django_sqlibrist takes engine and connection from django project settings

 0.1.4 django_sqlibrist configurator fixed

 0.1.3 django_sqlibrist configurator fixed

 0.1.2 LazyConfig fixed

 0.1.1 fixed loading config file

 0.1.0 django_sqlibrist gets DB connection settings from Django project's settings instead of config file

 0.0.7 django_sqlibrist moved to separate package and is importable in settings.py as "django_sqlibrist"