CREATE TABLE "packages"
(
    "name"              TEXT    NOT NULL,
    "hash"              TEXT    NOT NULL,
    "shortdesc"         TEXT    NOT NULL,
    "metadata"          TEXT    NOT NULL,
    "recipe"            TEXT,
    PRIMARY KEY ("hash", "name")
);
