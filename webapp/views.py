import datetime
import os
import random
import numpy as np
import string

from flask import *
from flask_login import current_user, login_required
from webapp import db
from .models import Record, batch_size, Encrypt, User
from .models import models as Mmodels

views = Blueprint("views", __name__)
training_levels = 1


def encrypt(raw):
    enc = Encrypt.query.filter_by(raw=raw).first()
    if not enc:
        enc = Encrypt(raw=raw, enc=''.join(random.choice(string.ascii_letters) for i in range(30)))
        db.session.add(enc)
        db.session.commit()
        return f"/enc/{enc.enc}"
    else:
        return f"/enc/{enc.enc}"


@views.route('/enc/<id>')
def send_image(id):
    raw = Encrypt.query.filter_by(enc=id).first().raw
    print(raw.lstrip("/"))
    return send_file(raw.lstrip("/"), mimetype='image/png')


def get_record_result(record):
    if record.choice == "option0":
        choice = record.option0
    elif record.choice == "option1":
        choice = record.option1
    else:
        choice = None

    if choice is not None:
        choice = int(choice.split("option")[1].rstrip(".png"))
        ans = int(record.helper.split("help")[1].rstrip(".png"))
        return (choice == ans)
    return None


def get_detail(user, pass_num, model):
    first_both=Record.query.filter(Record.choice=="bothOfThem").first()

    if user.is_admin == 0:
        records = Record.query.filter(
            Record.helper.contains(model + "_help"),
            Record.user_id == user.id,
            Record.pass_num == pass_num,
            Record.starting_time > first_both.starting_time).all()
    else:
        records = Record.query.filter(
            Record.helper.contains(model + "_help"),
            Record.pass_num == pass_num,
            Record.starting_time > first_both.starting_time).all()

    count = 0
    correct = 0
    for record in records:
        if User.query.filter(User.id==record.user_id).first().is_admin == 0:
            is_correct = get_record_result(record)
            if not is_correct is None:
                correct += is_correct
                count += 1
    return {"accuracy": round(correct / count * 100, 1) if count > 0 else 0, "count": count}


def get_average(dic):
    count = 0
    summ = 0
    for model in dic:
        count += dic[model]['count']
        summ += dic[model]['accuracy'] * dic[model]['count']
    return {"accuracy": round(summ / count, 1) if count != 0 else 0, "count": count}


def get_results(user):
    results = {}
    for pass_num in ["first pass", "second pass"]:
        results[pass_num] = {}
        for model in Mmodels:
            results[pass_num][model] = get_detail(user, pass_num, model)
        results[pass_num]["AVG"] = get_average(results[pass_num])
    return results


def get_all_user_results():
    results = {}
    for user in User.query.filter().all():
        if user.is_admin == 0:
            results[user.email] = get_results(user)
    return results


def get_time_deltas(user):
    time_deltas = {}
    for model in Mmodels:
        time_deltas[model] = []
        records = Record.query.filter(
            Record.helper.contains(model + "_help"),
            Record.user_id == user.id,
            Record.id != user.current_task).all()
        for record in records:
            delta = (record.ending_time - record.starting_time).total_seconds()
            print(delta)
            time_deltas[model].append(delta)
    return time_deltas


def time_deltas_to_bins(time_deltas):
    bin_edges = range(0, 15, 1)
    counts = {}
    for key in time_deltas:
        counts[key], _ = np.histogram(time_deltas[key], bins=bin_edges)
        counts[key] = counts[key].tolist()
    return counts, bin_edges


def get_progress(user):
    taskCount = len(Record.query.filter_by(user_id=user.id).all())
    #     samples_count=len([name for name in os.listdir("webapp/static/images") if
    #                  os.path.isdir(f"webapp/static/images/{name}") and "Training_sample" not in name])
    #     return f"progress: {max(0,min(taskCount, samples_count))}/{samples_count} | {max(0,min(taskCount-samples_count, samples_count))}/{samples_count} | " \
    #            f"{max(0,min(taskCount-2*samples_count, 2*samples_count))}/{samples_count*2}"
    return ((taskCount - 1) % batch_size + 1, batch_size)


@views.route("/")
def home():
    if current_user.is_authenticated and current_user.is_trained >= training_levels:
        if current_user.current_task != -1:
            record_id = current_user.current_task
            record = Record.query.filter_by(id=record_id).first()
            return render_template("home.html",
                                   user=current_user, sample=record.sample, option1=encrypt(record.option1),
                                   option0=encrypt(record.option0),
                                   helper=record.helper, progress=get_progress(current_user))
        else:
            taskCount = len(Record.query.filter_by(user_id=current_user.id).all())
            if taskCount == current_user.allowed_tasks:
                return render_template("askForTask.html", user=current_user, batch_size=batch_size)

            base_dir = "/static/images"
            all_samples = [name for name in os.listdir("webapp/static/images") if
                           os.path.isdir(f"webapp/static/images/{name}") and "Training_sample" not in name]
            all_models = Mmodels
            random.shuffle(all_samples)
            random.shuffle(all_models)
            print(all_models, all_samples)
            # first pass (new sample)
            for model in all_models:
                for sample in all_samples:
                    full_sample = f"{base_dir}/{sample}"
                    if not Record.query.filter_by(user_id=current_user.id, sample=f"{full_sample}").first():
                        option0 = f"{full_sample}/option0.png"
                        option1 = f"{full_sample}/option1.png"
                        options = [option0, option1]
                        random.shuffle(options)
                        option0, option1 = options
                        helper = f"{full_sample}/{model}_help{random.randint(0, 1)}.png"

                        record = Record(pass_num="first pass", user_id=current_user.id, sample=f"{full_sample}",
                                        helper=helper,
                                        option0=option0, option1=option1)
                        db.session.add(record)
                        db.session.commit()
                        current_user.current_task = record.id
                        db.session.commit()

                        print("First pass", current_user.id, full_sample, option1, option0, helper)
                        return render_template("home.html",
                                               user=current_user, sample=full_sample, option1=encrypt(record.option1),
                                               option0=encrypt(record.option0),
                                               helper=helper, progress=get_progress(current_user))
            # Second pass (new model)
            for model in all_models:
                for sample in all_samples:
                    full_sample = f"{base_dir}/{sample}"
                    helper0 = f"{full_sample}/{model}_help0.png"
                    helper1 = f"{full_sample}/{model}_help1.png"

                    if not Record.query.filter_by(user_id=current_user.id, sample=full_sample, helper=helper0).first():
                        if not Record.query.filter_by(user_id=current_user.id, sample=full_sample,
                                                      helper=helper1).first():
                            option0 = f"{full_sample}/option0.png"
                            option1 = f"{full_sample}/option1.png"
                            options = [option0, option1]
                            random.shuffle(options)
                            option0, option1 = options
                            helper = f"{full_sample}/{model}_help{random.randint(0, 1)}.png"

                            record = Record(pass_num="second pass", user_id=current_user.id, sample=full_sample,
                                            helper=helper, option0=option0,
                                            option1=option1)
                            db.session.add(record)
                            db.session.commit()
                            current_user.current_task = record.id
                            db.session.commit()

                            print("Second pass", current_user.id, full_sample, option1, option0, helper)
                            return render_template("home.html",
                                                   user=current_user, sample=full_sample,
                                                   option1=encrypt(record.option1),
                                                   option0=encrypt(record.option0),
                                                   helper=helper, progress=get_progress(current_user))
            #             print("Third pass")
            #             # Third pass (new helper)
            #             for model in all_models:
            #                 for sample in all_samples:
            #                     full_sample = f"{base_dir}/{sample}"
            #                     helpers = [f"{full_sample}/{model}_help0.png", f"{full_sample}/{model}_help1.png"]
            #                     random.shuffle(helpers)
            #                     for helper in helpers:
            #                         if not Record.query.filter_by(user_id=current_user.id, sample=full_sample,
            #                                                       helper=helper).first():
            #                             option0 = f"{full_sample}/option0.png"
            #                             option1 = f"{full_sample}/option1.png"
            #                             options = [option0, option1]
            #                             random.shuffle(options)
            #                             option0, option1 = options

            #                             record = Record(pass_num="third pass", user_id=current_user.id, sample=full_sample,
            #                                             helper=helper, option0=option0,
            #                                             option1=option1)
            #                             db.session.add(record)
            #                             db.session.commit()
            #                             current_user.current_task = record.id
            #                             db.session.commit()

            #                             print("Third pass", current_user.id, full_sample, option1, option0, helper)
            #                             return render_template("home.html",
            #                                                    user=current_user, sample=full_sample, option1=encrypt(record.option1),
            #                                    option0=encrypt(record.option0),
            #                                                    helper=helper, progress=get_progress(current_user))

            flash(f"Thank you for your collaboration. We ran out of samples!", category="success")
            return render_template("finished.html", user=current_user)
    elif current_user.is_authenticated and current_user.is_trained < training_levels:
        return redirect(f"/training/{current_user.is_trained}")
    else:
        return render_template("home.html", user=current_user)


@views.route('/training/<level>', methods=['GET'])
@login_required
def training(level):
    if request.method == 'GET':
        return render_template(f"training{level}.html", user=current_user)


@views.route('/FinishTraining', methods=['POST'])
@login_required
def finishTraining():
    if request.method == 'POST':
        current_user.is_trained += 1
        if current_user.is_trained >= training_levels:
            flash(f"Thanks for finishing the training. lets start the real evaluation.", category="success")
        db.session.commit()

        return redirect("/")


@views.route('/settings', methods=['GET'])
@login_required
def settings():
    if request.method == 'GET':
        results = get_results(current_user)
        counts, bin_edges = time_deltas_to_bins(get_time_deltas(current_user))
        print(counts, bin_edges)
        if current_user.is_admin == 1:
            return render_template(f"setting.html",
                                   taskCount=len(Record.query.filter_by(user_id=current_user.id).all()),
                                   user=current_user, results=results, models=Mmodels + ["AVG"],
                                   counts=counts, bins=list(bin_edges), all_user_results=get_all_user_results())
        else:
            return render_template(f"setting.html",
                                   taskCount=len(Record.query.filter_by(user_id=current_user.id).all()),
                                   user=current_user, results=results, models=Mmodels + ["AVG"],
                                   counts=counts, bins=list(bin_edges))


@views.route('/all_answers', methods=['GET'])
@login_required
def allAnswers():
    if request.method == 'GET':
        results = Record.query.filter(Record.user_id == current_user.id, Record.id != current_user.current_task).all()
        return render_template(f"all_answers.html",
                               user=current_user, results=results, models=Mmodels,
                               )


@views.route('/resetTraining', methods=['POST'])
@login_required
def resetTraining():
    if request.method == 'POST':
        current_user.is_trained = 0
        db.session.commit()
        return redirect("/")


@views.route('/removeAllAnswers', methods=['POST'])
@login_required
def removeAllAnswers():
    if request.method == 'POST':
        Record.query.filter_by(user_id=current_user.id).delete()
        current_user.current_task = -1
        current_user.allowed_tasks = batch_size
        db.session.commit()
        return redirect("/")


@views.route('/ignoreAnswers', methods=['POST'])
@login_required
def ignoreUser():
    if request.method == 'POST':
        user_email=request.form.get("email")
        print('/ignoreAnswers ', user_email)
        user = User.query.filter_by(email=user_email).first()
        user.is_admin = -1


        db.session.commit()
        return redirect("/settings")


@views.route('/add_batch', methods=['POST'])
@login_required
def addBatch():
    if request.method == 'POST':
        current_user.allowed_tasks += batch_size
        db.session.commit()
        return redirect("/")


@views.route('/submit_answer', methods=['POST'])
@login_required
def submit_answer():
    if request.method == 'POST' and current_user.current_task != -1:
        choice = request.form.get("selectedImage")
        record_id = current_user.current_task
        record = Record.query.filter_by(id=record_id).first()
        print(record_id, choice)
        record.choice = choice
        record.ending_time = datetime.datetime.utcnow()
        current_user.current_task = -1
        db.session.commit()
        # if get_record_result(record):
        #     flash(f"Correct", category="success")
        # else:
        #     flash(f"Wrong", category="error")
        print(record.id, record.user_id, record.ending_time, record.sample)

        return redirect("/")
    else:
        return redirect("/")


@views.route('/noneOfThem', methods=['POST'])
@login_required
def submit_answer_none():
    if request.method == 'POST' and current_user.current_task != -1:
        record_id = current_user.current_task
        record = Record.query.filter_by(id=record_id).first()
        record.choice = "none"
        record.ending_time = datetime.datetime.utcnow()
        current_user.current_task = -1
        db.session.commit()
        print(record.id, record.user_id, record.ending_time, record.sample)

        return redirect("/")
    else:
        return redirect("/")


@views.route('/bothOfThem', methods=['POST'])
@login_required
def submit_answer_both():
    if request.method == 'POST' and current_user.current_task != -1:
        record_id = current_user.current_task
        record = Record.query.filter_by(id=record_id).first()
        record.choice = "none"
        record.ending_time = datetime.datetime.utcnow()
        current_user.current_task = -1
        db.session.commit()
        print(record.id, record.user_id, record.ending_time, record.sample)

        return redirect("/")
    else:
        return redirect("/")
