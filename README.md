# Profile Management and Query API

A modern, async REST API for managing demographic profiles with intelligent natural language query parsing capabilities.

## Features

- **Intelligent Query Search**: Parse natural language-like queries (e.g., "young male or female above 30")
- **Async Architecture**: Full async/await support with AsyncPG for high-performance database operations
- **Advanced Filtering**: Filter by gender, age group, country, age range, and probability thresholds
- **Pagination & Sorting**: Flexible pagination with configurable page sizes and multiple sort options
- **Comprehensive Testing**: Full test suite with async fixtures and database seeding
- **Error Handling**: Intuitive error messages that describe what went wrong to the user

## Performance Considerations

- **Async/Await**: Non-blocking database operations
- **Connection Pooling**: SQLAlchemy manages connection pooling
- **Strategic Indexing**: Composite indexes on frequently filtered columns
- **Pagination**: Default limit of 10 prevents large result sets
- **Query Optimization**: Efficient LIKE patterns for text search

## Technology Stack

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Uvicorn](https://img.shields.io/badge/Uvicorn-4B8BBE?style=for-the-badge&logo=uvicorn&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-2C3E50?style=for-the-badge&logo=pydantic&logoColor=white)
![Postgres](https://img.shields.io/badge/Postgres-336791?style=for-the-badge&logo=postgresql&logoColor=white)

## Installation

### Prerequisites

- Python 3.10+
- PostgreSQL 12+
- pip or poetry

### Setup

1. **Clone or navigate to the project directory**
   ```bash
   cd "HNG Stage2 Task"
   ```

2. **Create and activate a virtual environment**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   - Copy `env-demo.txt` to `.env`:
     ```bash
     cp env-demo.txt .env
     ```
   - Update `.env` with your database credentials:
     ```env
     SYNC_DB_URL=postgresql+psycopg2://user:password@localhost/your_database
     ASYNC_DB_URL=postgresql+asyncpg://user:password@localhost/your_database
     ASYNC_TEST_DB_URL=postgresql+asyncpg://user:password@localhost/your_test_database
     ```

5. **Create database**
   ```sql
   createdb your_database
   createdb your_test_database  # For running tests
   ```

6. **Run migrations**
   ```bash
   alembic upgrade head
   ```

7. **Seed the database (optional)**
   ```bash
   python -m app.api.scripts.seed_db
   ```

## Usage

### Start the Server

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

- **API Docs**: `http://localhost:8000/docs` (Swagger UI)
- **Alternative Docs**: `http://localhost:8000/redoc` (ReDoc)

### Deployed

- [Live App](https://hng-stage2-task-production-11e5.up.railway.app)

- [API Documentation](https://hng-stage2-task-production-11e5.up.railway.app/docs)

## Testing

Run the test suite with pytest:

```bash
# Run all tests
pytest test/

# Run specific test file
pytest test/test_profiles.py
```

## Natural Language Parsing

Natural languages are parsed and converted to their underlying filter which are used to query the database for specific profiles.

### Processing Steps

- The received query words are normalized to remove `s` suffix from words and also exclude unsupported keywords
- Each normalized keyword is mapped against its filter, identified by the keyword's class (gender, age_group, etc.)
- The mapped keywords are then used to filter the profiles in the database to return only profiles that meet the requirements
- A QueryError exception is raised when invalid keywords are detected or when the keywords are arranged in a way that go against the rules

### Supported Keywords and Their Mapped Filters

#### Gender

- **Keywords**: `male`, `female`
- **Example**: gender=male

#### Age Groups

- **Keywords**: `child`, `teenager`, `adult`, `senior`, `young`
- **Example**: age_group=adult
- **Note**: The keyword `young` maps to ages 16-24 (e.g., age >= 16 and age <= 24)

#### Range Operators

- **Keywords**: `above`, `below`, `equal`, `minimum`, `maximum`, `between`
- **Operator Mappings**:
  - `above`: >
  - `below`: <
  - `equal`: =
  - `minimum`: >=
  - `maximum`: <=
  - `between`: >= and <=

#### Logical Operators

- **Keywords**: `or`, `and`

#### Country Names

- Full country names (e.g., "United States", "Nigeria")

### Example Queries

- `"young male"` → Males aged 16-24
- `"female above 30"` → Females 30 and above
- `"adults or senior"` → Adults or seniors
- `"males between 25 and 60"` → Males aged 25-60
- `"females from United States"` → Females from the US

### Rules

- ISO country codes (alpha_2 and alpha_3) are not supported
- Age values should be passed as positive integers. Floating point numbers and words are not supported
- When different values are passed for the same field (gender, age_group, etc.), the second value takes precedence over the first. An exception to this is when the two values are passed as operands to the `or` logical operator
- When range keywords are used, they should come before the age value (e.g., "male above 20" and not "male 20 and above")

### Limitations

- No support for name queries
- Only support for English words
- No support for country ISO code
- No normalization for words with `es` suffix
- No identification of age values when written as words
- No filter mapping for probability fields (min_gender_probability, min_country_probability) and support for float

## Troubleshooting

### Database Connection Issues

**Problem**: `could not connect to server`

**Solution**:
- Verify PostgreSQL is running: `pg_isready`
- Check database URL in `.env`
- Ensure database and user exist: `psql -l -U postgres`

### Migration Issues

**Problem**: Migration fails to apply

**Solution**:
```bash
# Check alembic version
alembic current

# Downgrade to previous version
alembic downgrade -1

# Review migration files in alembic/versions/
```

### Virtual Environment Issues

**Problem**: `ModuleNotFoundError` after installing dependencies

**Solution**:
- Ensure virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt --force-reinstall`
