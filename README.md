🏦 SmartBank - User Registration & KYC

A backend design for the User Registration & KYC module of a banking system.
This focuses on allowing customers to securely register, upload KYC details, and manage their profile.

📌 Use Case: User Registration & KYC

Goal: Allow customers to create an account and store their KYC information securely in the database.

Actors:

Customer: Registers and submits KYC details.

Bank Admin: Can view user profiles and verify KYC (future module).

API Design:

| Method | Endpoint         | Description         | Request Body                                                                                        | Response                                                            |
| ------ | ---------------- | ------------------- | --------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| POST   | `/auth/register` | Register a new user | `json { "name": "Sabarish", "email": "saba@gmail.com", "password": "12345", "kyc_id": "AB12345" } ` | `json { "message": "User registered successfully", "user_id": 1 } ` |
Database Design
| Field             | Type    | Description                       |
| ----------------- | ------- | --------------------------------- |
| `id`              | Integer | Primary Key, unique user ID       |
| `name`            | String  | Full name of the customer         |
| `email`           | String  | Unique email address              |
| `hashed_password` | String  | Hashed password (bcrypt)          |
| `kyc_id`          | String  | KYC document ID                   |
| `is_verified`     | Boolean | Optional, KYC verification status |
