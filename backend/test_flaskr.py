import os
import unittest
import json
from flask_sqlalchemy import SQLAlchemy

from flaskr import create_app
from models import setup_db, Question, Category


class TriviaTestCase(unittest.TestCase):
    """This class represents the trivia test case"""

    def setUp(self):
        """Define test variables and initialize app."""
        self.app = create_app()
        self.client = self.app.test_client
        self.database_name = "trivia_test"
        self.database_path = "postgres://{}:{}@{}/{}".format('postgres', 'password', 'localhost:5432',
                                                             self.database_name)
        setup_db(self.app, self.database_path)

        # binds the app to the current context
        with self.app.app_context():
            self.db = SQLAlchemy()
            self.db.init_app(self.app)
            # create all tables
            self.db.create_all()

            # cleans database before adding new records
            self.db.session.query(Question).delete()
            self.db.session.commit()
            self.db.session.query(Category).delete()
            self.db.session.commit()

            # adds categories
            self.db.engine.execute("insert into categories (id, type) values (1, 'Animals')")
            self.db.engine.execute("insert into categories (id, type) values (2, 'Math');")
            self.db.engine.execute("insert into categories (id, type) values (3, 'Science');")
            self.db.engine.execute("insert into categories (id, type) values (4, 'Disney');")
            self.db.engine.execute("insert into categories (id, type) values (5, 'Sci-Fi');")

            # adds a row to be deleted in the "test_delete_question" function
            self.db.engine.execute(
                "insert into questions (id, question, answer, category_id, difficulty) "
                "values (1, '2+2', '4', 2, 4);")

            # adds a row to be searched in the "test_search_questions" function
            self.db.engine.execute(
                "insert into questions (id, question, answer, category_id, difficulty) "
                "values (2, 'What country borders the US to the North?', 'Canada', 2, 4);")


    def tearDown(self):
        """Executed after each test"""
        pass

    # GET Requests
    # ______________________________________________________________________
    def test_get_categories(self):
        res = self.client().get('/api/v1/categories')
        data = json.loads(res.data)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(data['success'], True)
        self.assertGreaterEqual(len(data['categories']), 0)

    def test_405_sent_not_allowed_method(self):
        res = self.client().post('/api/v1/categories')

        self.assertEqual(res.status_code, 405)

    def test_get_questions(self):
        res = self.client().get('/api/v1/questions')
        data = json.loads(res.data)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(data['success'], True)
        self.assertGreaterEqual(len(data['categories']), 0)
        self.assertGreaterEqual(len(data['questions']), 0)
        self.assertGreaterEqual(data['total_questions'], 0)
        self.assertEqual(data['current_category'], None)

    def test_404_get_questions_bad_page(self):
        res = self.client().get('/api/v1/questions?page=1000')

        self.assertEqual(res.status_code, 404)

    def test_get_questions_by_category(self):
        res = self.client().get('/api/v1/categories/1/questions')
        data = json.loads(res.data)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(data['success'], True)
        self.assertGreaterEqual(len(data['questions']), 0)
        self.assertGreaterEqual(data['total_questions'], 0)
        self.assertEqual(data['current_category'], 1)

    def test_404_category_does_not_exist(self):
        res = self.client().get('/api/v1/categories/1000/questions')
        data = json.loads(res.data)

        self.assertEqual(res.status_code, 404)
        self.assertEqual(data['success'], False)
        self.assertEqual(data['category_id'], 1000)
        self.assertEqual(data['message'], "The category specified in the URL doesn't exist. Please resubmit with "
                                          "a correct category id.")
        self.assertEqual(data['status'], 404)

    # DELETE Requests
    # __________________________________________________________________________________________________________

    def test_delete_question(self):
        res = self.client().delete('/api/v1/questions/1')

        self.assertEqual(res.status_code, 204)

    # POST Requests
    # __________________________________________________________________________________________________________

    def test_post_new_questions(self):
        json_input = {
            "question": "2+2",
            "answer": "4",
            "category_id": 1,
            "difficulty": 1
        }
        res = self.client().post('/api/v1/questions', json=json_input)
        data = json.loads(res.data)

        self.assertEqual(res.status_code, 201)
        self.assertEqual(len(data["question_input"]), 4)
        self.assertEqual(data["success"], True)
        self.assertEqual(data["status"], 201)
        self.assertEqual(data["message"], "The question was added to the database")

    def test_422_post_incomplete_json(self):
        json_input = {
            "question": "2+2",
            "answer": "4",
            "difficulty": 1
        }
        res = self.client().post('/api/v1/questions', json=json_input)
        data = json.loads(res.data)

        self.assertEqual(res.status_code, 422)
        self.assertEqual(len(data["question_input"]), 3)
        self.assertEqual(data["success"], False)
        self.assertEqual(data["status"], 422)
        self.assertGreaterEqual(len(data["message"]), 0)

    def test_search_questions(self):
        json_input = {
            "search_term": "country"
        }
        res = self.client().post('/api/v1/questions/search', json=json_input)
        data = json.loads(res.data)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(data['questions']), 1)
        self.assertEqual(data['current_category'], None)
        self.assertEqual(data['status'], 200)

    def test_422_search_with_bad_json(self):
        json_input = {
            "search_term": None
        }
        res = self.client().post('/api/v1/questions/search', json=json_input)
        data = json.loads(res.data)

        self.assertEqual(res.status_code, 400)
        self.assertEqual(data['success'], False)
        self.assertEqual(data['status'], 400)
        self.assertGreaterEqual(len(data['message']), 0)

    '''
        Testing the play_quiz endpoint
    '''

    def test_play_quiz_all_categories(self):
        json_input = {
            "previous_questions": [1],
            "quiz_category": {"type": "click"}
        }
        res = self.client().post('/api/v1/quizzes', json=json_input)
        data = json.loads(res.data)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(data['question']), 5)
        self.assertEqual(data['questions_per_play'], 2)
        self.assertEqual(data['status'], 200)
        self.assertEqual(data['success'], True)

    def test_play_quiz_category_2(self):
        json_input = {
            "previous_questions": [1],
            "quiz_category": {"type": {"id": 2,
                                       "type": "Math"}}
        }
        res = self.client().post('/api/v1/quizzes', json=json_input)
        data = json.loads(res.data)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(data['question']), 5)
        self.assertEqual(data['questions_per_play'], 2)
        self.assertEqual(data['status'], 200)
        self.assertEqual(data['success'], True)

    def test_422_incomplete_json_play_quiz(self):
        json_input = {
            "quiz_category": {"type": "click"}
        }
        res = self.client().post('/api/v1/quizzes', json=json_input)
        data = json.loads(res.data)

        self.assertEqual(res.status_code, 422)
        self.assertEqual(data['success'], False)
        self.assertEqual(data['status'], 422)
        self.assertGreaterEqual(len(data['message']), 0)

    def test_422_bad_quiz_category_play_quiz(self):
        json_input = {
            "previous_questions": [1],
            "quiz_category": {"type": "all"}
        }
        res = self.client().post('/api/v1/quizzes', json=json_input)
        data = json.loads(res.data)

        self.assertEqual(res.status_code, 422)
        self.assertEqual(data['success'], False)
        self.assertEqual(data['status'], 422)
        self.assertGreaterEqual(len(data['message']), 0)

    def test_422_no_dict_in_type_play_quiz(self):
        json_input = {
            "previous_questions": [1],
            "quiz_category": {"type": ["hello"]}
        }
        res = self.client().post('/api/v1/quizzes', json=json_input)
        data = json.loads(res.data)

        self.assertEqual(res.status_code, 422)
        self.assertEqual(data['success'], False)
        self.assertEqual(data['status'], 422)
        self.assertGreaterEqual(len(data['message']), 0)

    def test_422_no_id_in_dict_in_type_play_quiz(self):
        json_input = {
            "previous_questions": [1],
            "quiz_category": {"type": {"hello": 1}}
        }
        res = self.client().post('/api/v1/quizzes', json=json_input)
        data = json.loads(res.data)

        self.assertEqual(res.status_code, 422)
        self.assertEqual(data['success'], False)
        self.assertEqual(data['status'], 422)
        self.assertGreaterEqual(len(data['message']), 0)

    def test_422_no_quiz_type_play_quiz(self):
        json_input = {
            "previous_questions": [1],
            "quiz_category": {"hello": 2}
        }
        res = self.client().post('/api/v1/quizzes', json=json_input)
        data = json.loads(res.data)

        self.assertEqual(res.status_code, 422)
        self.assertEqual(data['success'], False)
        self.assertEqual(data['status'], 422)
        self.assertGreaterEqual(len(data['message']), 0)

    def test_422_large_quiz_category_play_quiz(self):
        json_input = {
            "previous_questions": [1],
            "quiz_category": {"type": {"id": 100}}
        }
        res = self.client().post('/api/v1/quizzes', json=json_input)
        data = json.loads(res.data)

        self.assertEqual(res.status_code, 422)
        self.assertEqual(data['success'], False)
        self.assertEqual(data['status'], 422)
        self.assertGreaterEqual(len(data['message']), 0)


# Make the tests conveniently executable
if __name__ == "__main__":
    unittest.main()
