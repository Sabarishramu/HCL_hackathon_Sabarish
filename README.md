User Registration API
Method	Endpoint	Description	Request Body	Response
POST	/auth/register	Register a new user	json { "name": "Sabarish", "email": "saba@gmail.com", "password": "12345", "kyc_id": "AB12345" }	json { "message": "User registered successfully", "user_id": 1 }

Flow:

User submits personal details (name, email, password, KYC).

System validates input and stores user in database.

Returns success message.
