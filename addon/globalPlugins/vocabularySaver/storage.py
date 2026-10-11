"""Versioned local JSON storage. No NVDA or wx dependency: unit-test this directly."""
import copy
import json
import os
from pathlib import Path
import tempfile
from uuid import uuid4

SCHEMA_VERSION = 1
MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_LESSONS = 500
MAX_ENTRIES = 20000


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


def validate(data):
    """Return a clean copy; reject unknown structure instead of dropping fields."""
    if not isinstance(data, dict) or set(data) != {'schemaVersion', 'lessons'}:
        raise DataError('Expected schemaVersion and lessons in the JSON file.')
    if type(data['schemaVersion']) is not int or data['schemaVersion'] != SCHEMA_VERSION:
        raise DataError('Unsupported schema version. This starter supports version 1.')
    lessons = data['lessons']
    if not isinstance(lessons, list) or len(lessons) > MAX_LESSONS:
        raise DataError(f'Lessons must be a list of at most {MAX_LESSONS} lessons.')
    clean = {'schemaVersion': SCHEMA_VERSION, 'lessons': []}
    identifiers, names = set(), set()
    count = 0
    for lesson in lessons:
        if not isinstance(lesson, dict) or set(lesson) != {'id', 'name', 'entries'}:
            raise DataError('Each lesson needs id, name and entries.')
        identifier = text(lesson['id'], 'Lesson ID', 100, True)
        name = text(lesson['name'], 'Lesson name', 100, True)
        if identifier in identifiers or name.casefold() in names:
            raise DataError('Duplicate lesson ID or lesson name.')
        identifiers.add(identifier)
        names.add(name.casefold())
        if not isinstance(lesson['entries'], list):
            raise DataError('Lesson entries must be a list.')
        output = {'id': identifier, 'name': name, 'entries': []}
        for entry in lesson['entries']:
            count += 1
            if count > MAX_ENTRIES:
                raise DataError(f'The file may contain at most {MAX_ENTRIES} entries.')
            if not isinstance(entry, dict) or set(entry) != {'id', 'word', 'meaning', 'notes'}:
                raise DataError('Each entry needs id, word, meaning and notes.')
            identifier = text(entry['id'], 'Entry ID', 100, True)
            if identifier in identifiers:
                raise DataError('Duplicate ID in the file.')
            identifiers.add(identifier)
            output['entries'].append({
                'id': identifier,
                'word': text(entry['word'], 'Word', 200, True),
                'meaning': text(entry['meaning'], 'Meaning', 2000, True),
                'notes': text(entry['notes'], 'Notes', 10000),
            })
        clean['lessons'].append(output)
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
        self.data = read_json(self.path) if self.path.exists() else {'schemaVersion': 1, 'lessons': []}

    @property
    def lessons(self):
        return copy.deepcopy(self.data['lessons'])

    def _commit(self, candidate):
        candidate = validate(candidate)
        # One recovery snapshot of the state before the most recent successful save.
        if self.path.exists():
            write_json(self.path.with_suffix('.previous.json'), self.data)
        write_json(self.path, candidate)
        self.data = candidate

    def add_lesson(self, name):
        identifier = str(uuid4())
        candidate = copy.deepcopy(self.data)
        candidate['lessons'].append({'id': identifier, 'name': name, 'entries': []})
        self._commit(candidate)
        return identifier

    def add_lesson_with_entry(self, name, word, meaning, notes):
        """Create the first lesson and vocabulary atomically, not in two saves."""
        lesson_id, entry_id = str(uuid4()), str(uuid4())
        candidate = copy.deepcopy(self.data)
        candidate['lessons'].append({
            'id': lesson_id, 'name': name,
            'entries': [{'id': entry_id, 'word': word, 'meaning': meaning, 'notes': notes}],
        })
        self._commit(candidate)
        return lesson_id, entry_id

    def put_entry(self, lesson_id, word, meaning, notes, entry_id=None):
        candidate = copy.deepcopy(self.data)
        lesson = next((x for x in candidate['lessons'] if x['id'] == lesson_id), None)
        if lesson is None:
            raise DataError('Lesson not found.')
        entry = {'id': entry_id or str(uuid4()), 'word': word, 'meaning': meaning, 'notes': notes}
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
        lesson = next((x for x in candidate['lessons'] if x['id'] == lesson_id), None)
        if lesson is None or not any(x['id'] == entry_id for x in lesson['entries']):
            raise DataError('Entry not found.')
        lesson['entries'] = [x for x in lesson['entries'] if x['id'] != entry_id]
        self._commit(candidate)

    def export(self, destination):
        destination = Path(destination)
        if destination.resolve() in {self.path.resolve(), self.path.with_suffix('.previous.json').resolve(), self.path.with_suffix('.before-import.json').resolve()}:
            raise DataError('Choose a separate backup file, not an internal storage file.')
        write_json(destination, self.data)

    def import_replace(self, source):
        candidate = read_json(source)  # Validate fully before touching current data.
        write_json(self.path.with_suffix('.before-import.json'), self.data)
        self._commit(candidate)
