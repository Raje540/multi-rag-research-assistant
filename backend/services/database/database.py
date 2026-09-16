from backend.services.database.connection import get_connection


def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            project_id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            research_domain VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS papers (
            paper_id SERIAL PRIMARY KEY,
            project_id INTEGER NOT NULL,
            title TEXT,
            authors TEXT,
            year INTEGER,
            filename VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            CONSTRAINT fk_project
                FOREIGN KEY (project_id)
                REFERENCES projects(project_id)
                ON DELETE CASCADE
        );
    """)

    conn.commit()
    cursor.close()
    conn.close()

    print("Database tables created successfully")


def get_paper_count(project_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM papers
        WHERE project_id = %s;
        """,
        (project_id,)
    )

    count = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    return count


def add_paper(project_id, title, authors, year, filename):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO papers (
            project_id,
            title,
            authors,
            year,
            filename
        )
        VALUES (%s, %s, %s, %s, %s)
        RETURNING paper_id;
        """,
        (project_id, title, authors, year, filename)
    )

    paper_id = cursor.fetchone()[0]

    conn.commit()
    cursor.close()
    conn.close()

    return paper_id