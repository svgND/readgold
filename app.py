from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Book, Post, Like, Chapter

app = Flask(__name__)
app.config['SECRET_KEY'] = 'readgold_secret_123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///readgold.db'

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        remember = 'remember' in request.form
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user, remember=remember)
            return redirect(url_for('dashboard'))
        flash('Неверный логин или пароль')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        user = User(username=username, email=email, password=password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('choose_role'))
    return render_template('register.html')

@app.route('/choose-role')
@login_required
def choose_role():
    return render_template('choose_role.html')

@app.route('/set-role/<role>')
@login_required
def set_role(role):
    if role in ['reader', 'author']:
        current_user.role = role
        db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'author':
        book_id = request.args.get('book_id', type=int)
        if book_id:
            my_books = Book.query.filter_by(author_id=current_user.id).all()
            selected_book = Book.query.get(book_id)
            return render_template('author.html', my_books=my_books, selected_book=selected_book)
    selected_genre = request.args.get('genre')
    if selected_genre:
        books = Book.query.filter_by(genre=selected_genre).all()
    else:
        books = Book.query.all()
    return render_template('books.html', books=books, selected_genre=selected_genre)

@app.route('/author')
@login_required
def author_cabinet():
    if current_user.role != 'author':
        return redirect(url_for('dashboard'))
    my_books = Book.query.filter_by(author_id=current_user.id).all()
    book_id = request.args.get('book_id', type=int)
    selected_book = Book.query.get(book_id) if book_id else None
    return render_template('author.html', my_books=my_books, selected_book=selected_book)

@app.route('/add-book', methods=['POST'])
@login_required
def add_book():
    title = request.form['title']
    description = request.form['description']
    genre = request.form['genre']
    book = Book(title=title, description=description, genre=genre, author_id=current_user.id)
    db.session.add(book)
    db.session.commit()
    flash('Книга опубликована! 🎉')
    return redirect(url_for('author_cabinet'))

@app.route('/add-chapter/<int:book_id>', methods=['POST'])
@login_required
def add_chapter(book_id):
    book = Book.query.get_or_404(book_id)
    if book.author_id != current_user.id:
        return redirect(url_for('dashboard'))
    number = request.form['number']
    title = request.form['title']
    content = request.form['content']
    chapter = Chapter(number=number, title=title, content=content, book_id=book_id)
    db.session.add(chapter)
    db.session.commit()
    flash(f'Глава {number} добавлена! 🎉')
    return redirect(url_for('author_cabinet', book_id=book_id))

@app.route('/book/<int:book_id>')
@login_required
def book(book_id):
    book = Book.query.get_or_404(book_id)
    book.views += 1
    db.session.commit()
    return render_template('book.html', book=book, current_chapter=None)

@app.route('/book/<int:book_id>/chapter/<int:chapter_id>')
@login_required
def read_chapter(book_id, chapter_id):
    book = Book.query.get_or_404(book_id)
    current_chapter = Chapter.query.get_or_404(chapter_id)
    return render_template('book.html', book=book, current_chapter=current_chapter)

@app.route('/comment/<int:book_id>', methods=['POST'])
@login_required
def add_comment(book_id):
    content = request.form['content']
    comment = Comment(content=content, user_id=current_user.id, book_id=book_id)
    db.session.add(comment)
    db.session.commit()
    return redirect(url_for('book', book_id=book_id))

@app.route('/like/<int:book_id>')
@login_required
def like_book(book_id):
    book = Book.query.get_or_404(book_id)
    already_liked = Like.query.filter_by(user_id=current_user.id, book_id=book_id).first()
    if not already_liked:
        like = Like(user_id=current_user.id, book_id=book_id)
        db.session.add(like)
        book.likes += 1
        db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/profile')
@login_required
def profile():
    posts = Post.query.filter_by(user_id=current_user.id).order_by(Post.id.desc()).all()
    books = Book.query.filter_by(author_id=current_user.id).all()
    total_likes = sum(b.likes for b in books)
    total_views = sum(b.views for b in books)
    return render_template('profile.html', posts=posts, books=books,
                           total_likes=total_likes, total_views=total_views)

@app.route('/update-bio', methods=['POST'])
@login_required
def update_bio():
    current_user.bio = request.form['bio']
    db.session.commit()
    return redirect(url_for('profile'))

@app.route('/add-post', methods=['POST'])
@login_required
def add_post():
    content = request.form['content']
    post = Post(content=content, user_id=current_user.id)
    db.session.add(post)
    db.session.commit()
    return redirect(url_for('profile'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/search')
@login_required
def search():
    query = request.args.get('q', '')
    if query:
        books = Book.query.filter(Book.title.ilike(f'%{query}%')).all()
    else:
        books = []
    return render_template('books.html', books=books, selected_genre=None, search_query=query)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)