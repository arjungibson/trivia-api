import os
from flask import Flask, request, abort, jsonify
from sqlalchemy import exc
from flask_cors import CORS
from random import choice
from models import *

from models import setup_db, Question, Category

QUESTIONS_PER_PAGE = 10


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__)
    setup_db(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    @app.after_request
    def after_request(response):
        response.headers.add("Access-Control-Allow-Headers",
                             "Content-Type, Authorization")
        response.headers.add("Access-Control-Allow-Headers",
                             "GET, POST, PATCH, DELETE, PUT")
        return response

    # GET Requests
    # ________________________________________________________________________

    @app.route("/api/v1/categories", methods=["GET"])
    def get_categories():
        categories = db.session.query(Category).all()
        category_list = [category.format() for category in categories]

        return jsonify({"categories": category_list,
                        "success": True}), 200

    @app.route("/api/v1/questions", methods=["GET"])
    def get_questions():
        page = request.args.get("page", default=1, type=int)

        # questions.items is used to create questions_list
        questions = db.session.query(Question).paginate(page,
                                                        QUESTIONS_PER_PAGE,
                                                        False)
        questions_list = [question.format() for question in questions.items]

        categories = db.session.query(Category).all()
        category_list = [category.format() for category in categories]

        if page > questions.pages and page > 1:
            abort(404)

        return jsonify({"questions": questions_list,
                        "categories": category_list,
                        "current_category": None,
                        "success": True,
                        "total_questions": questions.total}), 200

    @app.route("/api/v1/categories/<int:category_id>/questions")
    def get_questions_by_category(category_id):

        category = db.session.query(Category).\
            filter(Category.id == category_id).first()

        # Creates exception if category_id does not exist
        if category is None:
            return jsonify({"category_id": category_id,
                            "success": False,
                            "status": 404,
                            "message": "The category specified in the URL "
                                       "doesn't exist. Please resubmit with "
                                       "a correct category id."}), 404

        questions = category.questions
        questions_list = [question.format() for question in questions]

        return jsonify({
            "questions": questions_list,
            "total_questions": len(questions_list),
            "current_category": category_id,
            "success": True
        })

    # DELETE Requests
    # ________________________________________________________________________

    @app.route("/api/v1/questions/<int:question_id>", methods=["DELETE"])
    def delete_question(question_id):
        question = db.session.query(Question).\
            filter(Question.id == question_id).first()

        if question is None:
            return jsonify({"question_id": question_id,
                            "success": False,
                            "status": 404,
                            "message": "The question specified in the URL"
                                       " doesn't exist. Please resubmit with "
                                       "a correct question id"}), 404
        try:
            Question.delete(question)
        except exc.SQLAlchemyError as e:
            return jsonify({"question_id": question_id,
                            "success": False,
                            "status": 422,
                            "message": f"{e.orig}"}), 422

        return app.response_class(status=204)

    # POST Requests
    # ________________________________________________________________________

    @app.route("/api/v1/questions", methods=["POST"])
    def post_new_question():

        body = request.get_json()

        try:
            new_question = Question(
                question=body.get("question", None),
                answer=body.get("answer", None),
                category_id=body.get("category_id", None),
                difficulty=body.get("difficulty", None)
            )

            Question.insert(new_question)
        except exc.SQLAlchemyError as e:
            return jsonify({"question_input": body,
                            "success": False,
                            "status": 422,
                            "message": f"{e.orig}"}), 422

        return jsonify({
            "question_input": body,
            "success": True,
            "status": 201,
            "message": "The question was added to the database"
        }), 201

    @app.route("/api/v1/questions/search", methods=["POST"])
    def search_questions():

        search_term = request.get_json().get("search_term")

        if search_term is None:
            abort(400)

        questions = db.session.query(Question)\
            .filter(Question.question.ilike("%" + search_term + "%")).all()
        question_list = [question.format() for question in questions]

        return jsonify({
            "questions": question_list,
            "total_questions": len(question_list),
            "current_category": None,
            "status": 200
        }), 200

    @app.route("/api/v1/quizzes", methods=["POST"])
    def play_quizzes():

        body = request.get_json()

        previous_questions = body.get("previous_questions", None)
        quiz_category_type = body.get("quiz_category").get("type", None)

        if previous_questions is None:
            abort(422)
        if quiz_category_type is None:
            abort(422)

        # Filters out the available question ids based on previous questions
        # The "click" type is for the ALL category
        if quiz_category_type == "click":
            ids = db.session.query(Question.id).all()
            filtered_ids = [i.id for i in ids if i.id not in previous_questions]
        else:
            if type(quiz_category_type) is not dict:
                abort(422)

            quiz_category_id = quiz_category_type.get("id", None)

            if quiz_category_id is None:
                abort(422)
            if type(quiz_category_id) is not int:
                abort(422)

            quiz_category_query_check = db.session.query(Category.id).\
                filter(Category.id == quiz_category_id).first()
            if quiz_category_query_check is None:
                abort(422)

            ids = db.session.query(Question.id) \
                .filter(Question.category_id == quiz_category_id).all()
            filtered_ids = [i.id for i in ids if i.id not in previous_questions]

        # Checks if there are no filtered ids before returning a response
        # No more filtered ids means its the end of the quiz
        if len(filtered_ids) == 0:
            questions_per_play = min(5, len(ids))
            return jsonify({"question": None,
                            "questions_per_play": questions_per_play,
                            "success": True,
                            "status": 200}), 200
        else:
            questions_per_play = min(5, len(ids))
            question_id = choice(filtered_ids)
            question = db.session.query(Question).\
                filter(Question.id == question_id).first()

            return jsonify({"question": Question.format(question),
                            "questions_per_play": questions_per_play,
                            "success": True,
                            "status": 200}), 200

    # Error Handlers
    # ____________________________________________________________________________________________________

    @app.errorhandler(400)
    def get_400_error(error):
        return jsonify({
            "success": False,
            "status": 400,
            "message": error.description
        }), 400

    @app.errorhandler(404)
    def get_404_error(error):
        return jsonify({
            "success": False,
            "status": 404,
            "message": error.description
        }), 404

    @app.errorhandler(422)
    def get_422_error(error):
        return jsonify({
            "success": False,
            "status": 422,
            "message": "The json that was sent did not include a proper field. "
                       "Please refer to documentation."
        }), 422

    @app.errorhandler(500)
    def get_500_error(error):
        return jsonify({
            "success": False,
            "status": 500,
            "message": error.description
        }), 500

    return app
