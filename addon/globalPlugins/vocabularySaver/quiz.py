"""Pure-Python word-to-meaning MCQ logic. No storage mutation or network calls."""
from dataclasses import dataclass
import random


class QuizError(ValueError):
    pass


@dataclass(frozen=True)
class Question:
    entry_id: str
    word: str
    options: tuple[str, ...]
    correct_index: int


def make_questions(lesson, rng=None, question_count=10):
    """Use only saved meanings as distractors; up to four options per question.

    Words with more than one distinct saved meaning are skipped, because a
    word-only question cannot distinguish those senses. Notes are not revealed.
    """
    if type(question_count) is not int or not 0 <= question_count <= 20000:
        raise QuizError('Question count must be 0 (all) or an integer from 1 to 20000.')
    rng = rng or random.Random()
    entries = lesson['entries']
    by_word = {}
    for entry in entries:
        by_word.setdefault(entry['word'].casefold(), set()).add(entry['meaning'].casefold())
    usable = [entry for entry in entries if len(by_word[entry['word'].casefold()]) == 1]
    meanings = {}
    for entry in usable:
        meanings.setdefault(entry['meaning'].casefold(), entry['meaning'])
    if len(meanings) < 2:
        raise QuizError('This lesson needs at least two distinct meanings for an MCQ quiz. '
                        'Words saved with conflicting meanings are skipped.')
    questions, seen_words = [], set()
    for entry in usable:
        normalized_word = entry['word'].casefold()
        if normalized_word in seen_words:
            continue  # Repeated identical vocabulary should not inflate the score.
        seen_words.add(normalized_word)
        distractors = [value for key, value in meanings.items() if key != entry['meaning'].casefold()]
        options = [entry['meaning']] + rng.sample(distractors, min(3, len(distractors)))
        rng.shuffle(options)
        questions.append(Question(entry['id'], entry['word'], tuple(options), options.index(entry['meaning'])))
    rng.shuffle(questions)
    return questions[:question_count] if question_count else questions


def score(questions, answers):
    if len(answers) != len(questions):
        raise QuizError('Answer every question before scoring.')
    for question, answer in zip(questions, answers):
        if type(answer) is not int or not 0 <= answer < len(question.options):
            raise QuizError('Choose one option for each question.')
    return sum(answer == question.correct_index for question, answer in zip(questions, answers))


def score_text(lesson_name, correct, total):
    if type(correct) is not int or type(total) is not int or not 0 <= correct <= total or total < 1:
        raise QuizError('Invalid score.')
    return (f'Vocabulary Saver - MCQ result\nLesson: {lesson_name}\n'
            f'Score: {correct}/{total} ({correct / total:.0%})\n'
            'Mode: word to meaning; saved vocabulary; local practice quiz.')
