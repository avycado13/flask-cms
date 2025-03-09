from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from flask_babel import Babel, lazy_gettext as _l
from flask_security import Security
from flask_moment import Moment
from flask_mail import Mail

security: Security = Security()
csrf: CSRFProtect = CSRFProtect()
db: SQLAlchemy = SQLAlchemy()
migrate: Migrate = Migrate()
# Babel for transalation
babel: Babel = Babel()
moment = Moment()
mail = Mail()
