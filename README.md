Project Description
The application management system is a web application for accounting and processing requests for document delivery within an organization. The application provides various interfaces for different user roles: administrators, moderators, couriers, and regular users.

Main functions
User Management:

Registration of new users

Changing roles and access rights

Password Reset

Working with applications:

Creating new applications

Editing existing applications

Tracking the status of applications

Archiving of completed applications

Special features:

Managing delivery addresses

Notification system

Search and filtering of applications

Exporting data

Technology stack
Backend: Python 3.10+

Framework: Flet (for creating a web interface)

Database: SQLite

Additional libraries:

bcrypt for hashing passwords

asyncio for asynchronous tasks

logging for logging

Project structure
request-management-system/
├── main.py            # Main application file

├── auth.py            # The authentication moduleи

├── roles.py           # Role and interface modulesв

├── database.py        # The database management module

├── requests.py        # The Application management module

└── README.md          #Documentation file

Configuring the database
When the application is launched for the first time, a database file is automatically created.the db is in the specified location (by default, Myapp\database.db).

The system creates:

A table of users with a pre-installed administrator (login: root, password: root1)

Tables for storing applications and archived applications

The address table

The notification table

Available User Roles
The administrator (admin):

Full access to all system functions

User Management

Viewing all applications

Moderator:

Application management

Archiving of completed applications

Viewing statistics

Courier:

Viewing assigned applications

A note about the completion of the delivery

Specifying the reasons for non-fulfillment

User (user):

Creating new applications

View your applications

Confirmation of receipt of documents

API Endpoints
The application uses the following routes:

/ - Login page

/register - Registration page

/admin - The Admin interface

/user - The User interface

/courier - The courier interface

/moderator - Moderator's interface

/create_request - Creating a new request

/profile - User profile

/archive - Archive of applications

License
This project is distributed under the MIT license. For more information, see the LICENSE file.
