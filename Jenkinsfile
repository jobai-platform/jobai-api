pipeline {
  agent any

  options {
    disableConcurrentBuilds()
    timestamps()
    buildDiscarder(logRotator(numToKeepStr: '20'))
  }

  environment {
    PYTHON_VERSION = '3.13'
    POETRY_VERSION = '2.1.4'
    DATABASE_URL = 'postgresql+asyncpg://jobai:jobai@localhost:5432/jobai_test'
    DATABASE_URL_TEST = 'postgresql+asyncpg://jobai:jobai@localhost:5432/jobai_test'
    JWT_SECRET = 'ci-test-secret-not-for-production'
    LINKEDIN_CLIENT_ID = 'dummy'
    LINKEDIN_CLIENT_SECRET = 'dummy'
    CI_POSTGRES = 'jobai-ci-postgres'
  }

  stages {
    stage('Prepare PostgreSQL') {
      steps {
        sh 'docker rm -f "$CI_POSTGRES" >/dev/null 2>&1 || true'
        sh '''
          docker run -d --name "$CI_POSTGRES" \
            -e POSTGRES_USER=jobai \
            -e POSTGRES_PASSWORD=jobai \
            -e POSTGRES_DB=jobai_test \
            -p 5432:5432 \
            pgvector/pgvector:pg16
        '''
        sh '''
          for i in $(seq 1 30); do
            docker exec "$CI_POSTGRES" pg_isready -U jobai -d jobai_test && exit 0
            sleep 2
          done
          docker logs "$CI_POSTGRES"
          exit 1
        '''
      }
    }

    stage('Install Dependencies') {
      steps {
        sh 'python3 --version'
        sh 'python3 -m pip install --upgrade pip'
        sh 'python3 -m pip install "poetry==$POETRY_VERSION"'
        sh 'poetry install --no-interaction --no-ansi --no-root'
      }
    }

    stage('Test') {
      steps {
        sh 'poetry run pytest -q'
      }
    }

    stage('Build Image') {
      steps {
        sh '''
          SHORT_SHA=$(git rev-parse --short HEAD)
          docker build \
            --build-arg POETRY_VERSION="$POETRY_VERSION" \
            -t "jobai-backend:${SHORT_SHA}" \
            -t jobai-backend:ci .
        '''
      }
    }
  }

  post {
    always {
      sh 'docker rm -f "$CI_POSTGRES" >/dev/null 2>&1 || true'
    }
  }
}
