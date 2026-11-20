"""Versioned local JSON storage. No NVDA or wx dependency: unit-test this directly.

Schema version 2 adds top-level languages and per-lesson language/level fields.
Version 3 adds an optional per-entry reading (for example the hiragana reading
of a Japanese word written with kanji).
Version 1 and 2 files are migrated in memory: version 1 lessons become
unassigned (languageId None, empty level) and the starter language list is
added; version 2 entries gain an empty reading. No lesson is ever assigned to
a language automatically.
"""
import copy
import json
import os
from pathlib import Path
import tempfile
from uuid import uuid4

SCHEMA_VERSION = 3
MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_LESSONS = 500
MAX_ENTRIES = 20000
MAX_LANGUAGES = 200

# Convenience list only: users can add, rename or delete languages freely.
STARTER_LANGUAGES = (
    'Japanese', 'English', 'Korean', 'Chinese', 'French',
    'German', 'Spanish', 'Russian', 'Italian',
)


class DataError(ValueError):
    """The file or an entered value is unsafe or unsupported."""


def text(value, label, limit, required=False):
    if not isinstance(value, str):
        raise DataError(f"{label} must be text.")
    value = value.strip()
    if required and not value:
        raise DataError(f"{label} is required.")
    if len(value) > limit:
        raise DataError(f"{label} must be at most {limit} characters.")
    if '\x00' in value:
        raise DataError(f"{label} contains a null character.")
    return value


def _clean_language(language, identifiers, names):
    if not isinstance(language, dict) or set(language) != {'id', 'name', 'custom'}:
        raise DataError('Each language needs id, name and custom.')
    identifier = text(language['id'], 'Language ID', 100, True)
    name = text(language['name'], 'Language name', 100, True)
    if type(language['custom']) is not bool:
        raise DataError('Language custom flag must be true or false.')
    if identifier in identifiers or name.casefold() in names:
        raise DataError('Duplicate language ID or language name.')
    identifiers.add(identifier)
    names.add(name.casefold())
    return {'id': identifier, 'name': name, 'custom': language['custom']}


def _clean_entries(entries, identifiers, count):
    if not isinstance(entries, list):
        raise DataError('Lesson entries must be a list.')
    output = []
    for entry in entries:
        count[0] += 1
        if count[0] > MAX_ENTRIES:
            raise DataError(f'The file may contain at most {MAX_ENTRIES} entries.')
        if not isinstance(entry, dict) or set(entry) != {'id', 'word', 'meaning', 'notes', 'reading'}:
            raise DataError('Each entry needs id, word, meaning, notes and reading.')
        identifier = text(entry['id'], 'Entry ID', 100, True)
        if identifier in identifiers:
            raise DataError('Duplicate ID in the file.')
        identifiers.add(identifier)
        output.append({
            'id': identifier,
            'word': text(entry['word'], 'Word', 200, True),
            'meaning': text(entry['meaning'], 'Meaning', 2000, True),
            'notes': text(entry['notes'], 'Notes', 10000),
            'reading': text(entry['reading'], 'Reading', 200),
        })
    return output


def _migrate_v1(data):
    """Wrap a version 1 structure into version 2, leaving lessons unassigned."""
    lessons = data['lessons']
    if not isinstance(lessons, list):
        raise DataError('Lessons must be a list.')
    migrated = {
        'schemaVersion': 2,
        'languages': [{'id': str(uuid4()), 'name': name, 'custom': False} for name in STARTER_LANGUAGES],
        'lessons': [
            {'id': lesson['id'], 'name': lesson['name'], 'languageId': None, 'level': '', 'entries': lesson['entries']}
            for lesson in lessons
        ],
    }
    return migrated


def _migrate_v2(data):
    """Add an empty reading to every version 2 entry."""
    lessons = data['lessons']
    if not isinstance(lessons, list):
        raise DataError('Lessons must be a list.')
    return {
        'schemaVersion': 3,
        'languages': data['languages'],
        'lessons': [
            {**lesson, 'entries': [{**entry, 'reading': ''} for entry in lesson['entries']]}
            for lesson in lessons
        ],
    }


def validate(data):
    """Return a clean version 3 copy; reject unknown structure instead of dropping fields."""
    if not isinstance(data, dict) or 'schemaVersion' not in data:
        raise DataError('Expected a schema version in the JSON file.')
    if type(data['schemaVersion']) is not int or not 1 <= data['schemaVersion'] <= SCHEMA_VERSION:
        raise DataError(f'Unsupported schema version. This add-on supports versions 1 to {SCHEMA_VERSION}.')
    if data['schemaVersion'] == 1:
        if set(data) != {'schemaVersion', 'lessons'}:
            raise DataError('Expected schemaVersion and lessons in the JSON file.')
        data = _migrate_v1(data)
    if data['schemaVersion'] == 2:
        if set(data) != {'schemaVersion', 'languages', 'lessons'}:
            raise DataError('Expected schemaVersion, languages and lessons in the JSON file.')
        data = _migrate_v2(data)
    elif set(data) != {'schemaVersion', 'languages', 'lessons'}:
        raise DataError('Expected schemaVersion, languages and lessons in the JSON file.')
    languages = data['languages']
    if not isinstance(languages, list) or len(languages) > MAX_LANGUAGES:
        raise DataError(f'Languages must be a list of at most {MAX_LANGUAGES} languages.')
    identifiers, names = set(), set()
    clean = {'schemaVersion': SCHEMA_VERSION, 'languages': [], 'lessons': []}
    for language in languages:
        clean['languages'].append(_clean_language(language, identifiers, names))
    language_ids = {language['id'] for language in clean['languages']}
    lessons = data['lessons']
    if not isinstance(lessons, list) or len(lessons) > MAX_LESSONS:
        raise DataError(f'Lessons must be a list of at most {MAX_LESSONS} lessons.')
    count = [0]
    for lesson in lessons:
        if not isinstance(lesson, dict) or set(lesson) != {'id', 'name', 'languageId', 'level', 'entries'}:
            raise DataError('Each lesson needs id, name, languageId, level and entries.')
        identifier = text(lesson['id'], 'Lesson ID', 100, True)
        name = text(lesson['name'], 'Lesson name', 100, True)
        if identifier in identifiers or name.casefold() in names:
            raise DataError('Duplicate lesson ID or lesson name.')
        identifiers.add(identifier)
        names.add(name.casefold())
        language_id = lesson['languageId']
        if language_id is not None:
            language_id = text(language_id, 'Lesson language ID', 100, True)
            if language_id not in language_ids:
                raise DataError('Lesson refers to an unknown language.')
        clean['lessons'].append({
            'id': identifier,
            'name': name,
            'languageId': language_id,
            'level': text(lesson['level'], 'Lesson level', 200),
            'entries': _clean_entries(lesson['entries'], identifiers, count),
        })
    return clean


def _no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise DataError(f'Duplicate JSON key: {key}')
        result[key] = value
    return result


def read_json(path):
    try:
        with Path(path).open('rb') as stream:
            raw = stream.read(MAX_FILE_BYTES + 1)
        if len(raw) > MAX_FILE_BYTES:
            raise DataError('File is larger than 5 MiB.')
        return validate(json.loads(raw.decode('utf-8-sig'), object_pairs_hook=_no_duplicate_keys))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise DataError('The file is not valid UTF-8 vocabulary JSON.') from error


def write_json(path, data):
    """Write and sync a temporary sibling, then atomically replace destination."""
    path = Path(path)
    clean = validate(data)
    raw = (json.dumps(clean, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    if len(raw) > MAX_FILE_BYTES:
        raise DataError('Data would exceed the 5 MiB storage limit.')
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self._pre_migration_backup = None
        self._pre_migration_version = None
        if self.path.exists():
            try:
                raw = self.path.read_bytes()
                if len(raw) > MAX_FILE_BYTES:
                    raise DataError('File is larger than 5 MiB.')
                original = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=_no_duplicate_keys)
            except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
                raise DataError('The file is not valid UTF-8 vocabulary JSON.') from error
            if isinstance(original, dict) and 1 <= original.get('schemaVersion', 0) < SCHEMA_VERSION:
                # Keep the pre-migration document so a downgrade to an older
                # add-on version can be undone by restoring this exact data.
                self._pre_migration_backup = original
                self._pre_migration_version = original['schemaVersion']
            self.data = validate(original)
        else:
            self.data = {
                'schemaVersion': SCHEMA_VERSION,
                'languages': [{'id': str(uuid4()), 'name': name, 'custom': False} for name in STARTER_LANGUAGES],
                'lessons': [],
            }

    @property
    def lessons(self):
        return copy.deepcopy(self.data['lessons'])

    @property
    def languages(self):
        return copy.deepcopy(self.data['languages'])

    def _commit(self, candidate):
        candidate = validate(candidate)
        if self._pre_migration_backup is not None:
            backup = self.path.with_suffix(f'.v{self._pre_migration_version}-backup.json')
            if not backup.exists():
                try:
                    raw = (json.dumps(self._pre_migration_backup, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
                    backup.write_bytes(raw)
                except OSError:
                    pass  # Retry on the next save; never block vocabulary writes.
                else:
                    self._pre_migration_backup = None
            else:
                self._pre_migration_backup = None
        # One recovery snapshot of the state before the most recent successful save.
        if self.path.exists():
            write_json(self.path.with_suffix('.previous.json'), self.data)
        write_json(self.path, candidate)
        self.data = candidate

    def _language(self, language_id):
        language = next((x for x in self.data['languages'] if x['id'] == language_id), None)
        if language is None:
            raise DataError('Language not found.')
        return language

    def add_language(self, name, custom=True):
        """Add a language; duplicate names (any case) are rejected."""
        candidate = copy.deepcopy(self.data)
        if len(candidate['languages']) >= MAX_LANGUAGES:
            raise DataError(f'At most {MAX_LANGUAGES} languages can be saved.')
        name = text(name, 'Language name', 100, True)
        if any(x['name'].casefold() == name.casefold() for x in candidate['languages']):
            raise DataError('A language with this name already exists.')
        identifier = str(uuid4())
        candidate['languages'].append({'id': identifier, 'name': name, 'custom': bool(custom)})
        self._commit(candidate)
        return identifier

    def rename_language(self, language_id, name):
        candidate = copy.deepcopy(self.data)
        language = next((x for x in candidate['languages'] if x['id'] == language_id), None)
        if language is None:
            raise DataError('Language not found.')
        name = text(name, 'Language name', 100, True)
        if any(x['id'] != language_id and x['name'].casefold() == name.casefold() for x in candidate['languages']):
            raise DataError('A language with this name already exists.')
        language['name'] = name
        language['custom'] = True
        self._commit(candidate)

    def delete_language(self, language_id):
        """Delete a language only while no lesson uses it; vocabulary is never deleted."""
        self._language(language_id)
        if any(x['languageId'] == language_id for x in self.data['lessons']):
            raise DataError('Lessons still use this language. Reassign or remove those lessons first.')
        candidate = copy.deepcopy(self.data)
        candidate['languages'] = [x for x in candidate['languages'] if x['id'] != language_id]
        self._commit(candidate)

    def _lesson(self, candidate, lesson_id):
        lesson = next((x for x in candidate['lessons'] if x['id'] == lesson_id), None)
        if lesson is None:
            raise DataError('Lesson not found.')
        return lesson

    def set_lesson_language(self, lesson_id, language_id):
        """Assign a lesson to a language, or pass None to make it unassigned."""
        if language_id is not None:
            self._language(language_id)
        candidate = copy.deepcopy(self.data)
        self._lesson(candidate, lesson_id)['languageId'] = language_id
        self._commit(candidate)

    def set_lesson_level(self, lesson_id, level):
        """Set a free-text exam/level label such as 'JLPT N5'; empty clears it."""
        candidate = copy.deepcopy(self.data)
        self._lesson(candidate, lesson_id)['level'] = level
        self._commit(candidate)

    def add_lesson(self, name, language_id=None, level=''):
        if language_id is not None:
            self._language(language_id)
        identifier = str(uuid4())
        candidate = copy.deepcopy(self.data)
        candidate['lessons'].append({'id': identifier, 'name': name, 'languageId': language_id, 'level': level, 'entries': []})
        self._commit(candidate)
        return identifier

    def add_lesson_with_entry(self, name, word, meaning, notes, language_id=None, level='', reading=''):
        """Create the first lesson and vocabulary atomically, not in two saves."""
        if language_id is not None:
            self._language(language_id)
        lesson_id, entry_id = str(uuid4()), str(uuid4())
        candidate = copy.deepcopy(self.data)
        candidate['lessons'].append({
            'id': lesson_id, 'name': name, 'languageId': language_id, 'level': level,
            'entries': [{'id': entry_id, 'word': word, 'meaning': meaning, 'notes': notes, 'reading': reading}],
        })
        self._commit(candidate)
        return lesson_id, entry_id

    def put_entry(self, lesson_id, word, meaning, notes, entry_id=None, reading=''):
        candidate = copy.deepcopy(self.data)
        lesson = self._lesson(candidate, lesson_id)
        entry = {'id': entry_id or str(uuid4()), 'word': word, 'meaning': meaning, 'notes': notes, 'reading': reading}
        if entry_id is None:
            lesson['entries'].append(entry)
        else:
            index = next((i for i, x in enumerate(lesson['entries']) if x['id'] == entry_id), None)
            if index is None:
                raise DataError('Entry not found.')
            lesson['entries'][index] = entry
        self._commit(candidate)
        return entry['id']

    def delete_entry(self, lesson_id, entry_id):
        candidate = copy.deepcopy(self.data)
        lesson = self._lesson(candidate, lesson_id)
        if not any(x['id'] == entry_id for x in lesson['entries']):
            raise DataError('Entry not found.')
        lesson['entries'] = [x for x in lesson['entries'] if x['id'] != entry_id]
        self._commit(candidate)

    def patch_entries(self, patches):
        """Apply reading/meaning-only changes (the AI check) in one save.

        Each patch needs lessonId and entryId plus a reading and/or a meaning.
        Word and notes are never changed here. Unknown IDs raise DataError and
        nothing is written.
        """
        if not patches:
            return 0
        candidate = copy.deepcopy(self.data)
        for patch in patches:
            lesson = self._lesson(candidate, patch['lessonId'])
            entry = next((x for x in lesson['entries'] if x['id'] == patch['entryId']), None)
            if entry is None:
                raise DataError('Entry not found.')
            if 'reading' in patch:
                entry['reading'] = patch['reading']
            if 'meaning' in patch:
                entry['meaning'] = patch['meaning']
        self._commit(candidate)
        return len(patches)

    def export(self, destination):
        destination = Path(destination)
        protected = {self.path.resolve(), self.path.with_suffix('.previous.json').resolve(),
                     self.path.with_suffix('.before-import.json').resolve(),
                     self.path.with_suffix('.v1-backup.json').resolve(),
                     self.path.with_suffix('.v2-backup.json').resolve()}
        if destination.resolve() in protected:
            raise DataError('Choose a separate backup file, not an internal storage file.')
        write_json(destination, self.data)

    def import_replace(self, source):
        candidate = read_json(source)  # Validate fully before touching current data.
        write_json(self.path.with_suffix('.before-import.json'), self.data)
        self._commit(candidate)
