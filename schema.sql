CREATE TABLE IF NOT EXISTS resumes (
  id INT AUTO_INCREMENT PRIMARY KEY,
  token CHAR(32) NOT NULL UNIQUE,
  name VARCHAR(120), email VARCHAR(160), phone VARCHAR(40), location VARCHAR(120),
  linkedin VARCHAR(255), github VARCHAR(255), summary TEXT,
  template VARCHAR(20), career_roles TEXT,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS education (
  id INT AUTO_INCREMENT PRIMARY KEY, resume_id INT NOT NULL,
  college VARCHAR(200), degree VARCHAR(100), branch VARCHAR(100), grad_year VARCHAR(10), cgpa VARCHAR(10),
  FOREIGN KEY (resume_id) REFERENCES resumes(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS skills (
  id INT AUTO_INCREMENT PRIMARY KEY, resume_id INT NOT NULL, skill VARCHAR(80),
  FOREIGN KEY (resume_id) REFERENCES resumes(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS projects (
  id INT AUTO_INCREMENT PRIMARY KEY, resume_id INT NOT NULL,
  title VARCHAR(200), description TEXT, tech VARCHAR(255), link VARCHAR(500),
  FOREIGN KEY (resume_id) REFERENCES resumes(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS experience (
  id INT AUTO_INCREMENT PRIMARY KEY, resume_id INT NOT NULL,
  company VARCHAR(200), role VARCHAR(150), duration VARCHAR(100), details TEXT,
  FOREIGN KEY (resume_id) REFERENCES resumes(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS certifications (
  id INT AUTO_INCREMENT PRIMARY KEY, resume_id INT NOT NULL,
  name VARCHAR(200), organisation VARCHAR(200), completed VARCHAR(20),
  FOREIGN KEY (resume_id) REFERENCES resumes(id) ON DELETE CASCADE
);
-- Cache of recent provider results (protects free-tier quotas). Not a source of "fake" jobs: rows expire.
CREATE TABLE IF NOT EXISTS job_listings (
  id INT AUTO_INCREMENT PRIMARY KEY, query_key CHAR(40) NOT NULL, provider VARCHAR(20),
  title VARCHAR(300), company VARCHAR(200), location VARCHAR(200), description TEXT,
  experience VARCHAR(100), job_type VARCHAR(60), remote TINYINT(1), url VARCHAR(1000),
  fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, INDEX (query_key)
);
