CREATE TABLE "installed_packages"
(
    "sys_gen" INTEGER NOT NULL,
    "name"    TEXT    NOT NULL,
    "hash"    TEXT    NOT NULL,
    FOREIGN KEY ("name", "hash") REFERENCES "packages" ("name", "hash") ON DELETE CASCADE,
    FOREIGN KEY ("sys_gen") REFERENCES "system_generations" ("id") ON DELETE CASCADE,
    PRIMARY KEY ("sys_gen", "name", "hash")
);

CREATE TABLE "packages"
(
    "name"              TEXT    NOT NULL,
    "hash"              TEXT    NOT NULL,
    "shortdesc"         TEXT    NOT NULL,
    "metadata"          TEXT    NOT NULL,
    "recipe"            TEXT,
    "source"            INTEGER NOT NULL,
    "source_generation" TEXT    NOT NULL,
    FOREIGN KEY ("source", "source_generation") REFERENCES "source_generations" ("source", "generation") ON DELETE CASCADE,
    PRIMARY KEY ("hash", "name")
);

CREATE TABLE "source_generations"
(
    "source"     INTEGER NOT NULL,
    "generation" TEXT    NOT NULL,
    FOREIGN KEY ("source") REFERENCES "sources" ("id") ON DELETE CASCADE,
    PRIMARY KEY ("source", "generation")
);

CREATE TABLE "sources"
(
    "id"        INTEGER NOT NULL,
    "name"      TEXT    NOT NULL,
    "generator" TEXT,
    PRIMARY KEY ("id" AUTOINCREMENT)
);

CREATE TABLE "system_generations"
(
    "id"           INTEGER NOT NULL,
    "alias"        TEXT,
    "date_created" TEXT    NOT NULL,
    "parent"       INTEGER,
    PRIMARY KEY ("id" AUTOINCREMENT),
    FOREIGN KEY ("parent") REFERENCES "system_generations" ("id") ON DELETE SET NULL
);