"""MCQ logic tests run without NVDA or wx."""
import copy
import importlib.util
from pathlib import Path
import random
import sys
import unittest

MODULE = Path(__file__).resolve().parents[1] / 'addon/globalPlugins/vocabularySaver/quiz.py'
spec = importlib.util.spec_from_file_location('quiz_under_test', MODULE)
quiz = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = quiz
spec.loader.exec_module(quiz)


def lesson(pairs):
    return {'id': 'lesson', 'name': 'Lesson 1', 'entries': [
        {'id': str(i), 'word': word, 'meaning': meaning, 'notes': ''}
        for i, (word, meaning) in enumerate(pairs)
    ]}


class QuizTests(unittest.TestCase):
    def test_default_ten_limit(self):
        data = lesson([(str(i), f'meaning {i}') for i in range(15)])
        self.assertEqual(len(quiz.make_questions(data)), 10)

    def test_custom_limit_and_all(self):
        data = lesson([(str(i), f'meaning {i}') for i in range(15)])
        self.assertEqual(len(quiz.make_questions(data, question_count=3)), 3)
        self.assertEqual(len(quiz.make_questions(data, question_count=0)), 15)
        self.assertEqual(len(quiz.make_questions(data, question_count=30)), 15)

    def test_invalid_question_count(self):
        data = lesson([('cat', 'animal'), ('water', 'liquid')])
        for count in [-1, True, 'all', 20001]:
            with self.subTest(count=count), self.assertRaises(quiz.QuizError):
                quiz.make_questions(data, question_count=count)

    def test_empty_or_one_meaning_rejected(self):
        for pairs in [[], [('cat', 'animal')], [('cat', 'animal'), ('dog', 'ANIMAL')]]:
            with self.subTest(pairs=pairs), self.assertRaises(quiz.QuizError):
                quiz.make_questions(lesson(pairs))

    def test_two_answers_per_question(self):
        questions = quiz.make_questions(lesson([('猫', 'cat'), ('犬', 'dog')]), random.Random(1))
        self.assertEqual(len(questions), 2)
        for question in questions:
            self.assertEqual(len(question.options), 2)
            self.assertEqual(set(question.options), {'cat', 'dog'})

    def test_up_to_four_answers(self):
        questions = quiz.make_questions(lesson([(str(i), f'meaning {i}') for i in range(10)]))
        self.assertEqual(len(questions), 10)
        self.assertTrue(all(len(q.options) == 4 and len(set(q.options)) == 4 for q in questions))

    def test_correct_answer_maps_to_saved_meaning(self):
        data = lesson([('猫', 'cat'), ('犬', 'dog'), ('水', 'water')])
        lookup = {entry['id']: entry['meaning'] for entry in data['entries']}
        for question in quiz.make_questions(data):
            self.assertEqual(question.options[question.correct_index], lookup[question.entry_id])

    def test_no_storage_mutation(self):
        data = lesson([('cat', 'animal'), ('water', 'liquid')])
        before = copy.deepcopy(data)
        quiz.make_questions(data)
        self.assertEqual(data, before)

    def test_ambiguous_words_skipped(self):
        questions = quiz.make_questions(lesson([('bank', 'river edge'), ('BANK', 'money institution'), ('cat', 'animal'), ('water', 'liquid')]))
        self.assertEqual({q.word for q in questions}, {'cat', 'water'})

    def test_identical_words_do_not_duplicate_questions(self):
        questions = quiz.make_questions(lesson([('cat', 'animal'), ('CAT', 'ANIMAL'), ('water', 'liquid')]))
        self.assertEqual(len(questions), 2)

    def test_deterministic_seed(self):
        data = lesson([(str(i), f'meaning {i}') for i in range(6)])
        self.assertEqual(quiz.make_questions(data, random.Random(5)), quiz.make_questions(data, random.Random(5)))

    def test_scores(self):
        questions = quiz.make_questions(lesson([('cat', 'animal'), ('water', 'liquid')]))
        self.assertEqual(quiz.score(questions, [q.correct_index for q in questions]), 2)
        self.assertEqual(quiz.score(questions, [(q.correct_index + 1) % len(q.options) for q in questions]), 0)

    def test_incomplete_invalid_answers(self):
        questions = quiz.make_questions(lesson([('cat', 'animal'), ('water', 'liquid')]))
        for answers in [[], [0], [0, -1], [0, 20], [False, 0]]:
            with self.subTest(answers=answers), self.assertRaises(quiz.QuizError):
                quiz.score(questions, answers)

    def test_shareable_text(self):
        result = quiz.score_text('Lesson 1', 2, 3)
        self.assertIn('Score: 2/3 (67%)', result)
        self.assertIn('Lesson: Lesson 1', result)
        self.assertNotIn('notes', result)

    def test_invalid_score(self):
        for values in [(0, 0), (3, 2), (-1, 3)]:
            with self.subTest(values=values), self.assertRaises(quiz.QuizError):
                quiz.score_text('Lesson', *values)


if __name__ == '__main__':
    unittest.main()
