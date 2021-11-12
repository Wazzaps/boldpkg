sqlite3 metadata.sqlite3 '.mode tabs' 'select name, shortdesc from packages'

sqlite3 metadata.sqlite3 '.mode tabs' 'select name, homepage from packages where name="hello" and hash="57oc2ku5bccucu5qwkmwrtud7zbcaggg"'
