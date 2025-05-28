import { beforeAll, afterAll } from 'vitest';
import { config } from 'dotenv';

// Load test environment variables
config({ path: '.env.test' });

beforeAll(async () => {
  // Global test setup
  console.log('Setting up test environment...');
  
  // Ensure test database is available
  if (!process.env.TEST_DB_NAME) {
    process.env.TEST_DB_NAME = 'task_manager_test';
  }
  
  if (!process.env.TEST_DB_USER) {
    process.env.TEST_DB_USER = 'test_user';
  }
  
  if (!process.env.TEST_DB_PASSWORD) {
    process.env.TEST_DB_PASSWORD = 'test_password';
  }
});

afterAll(async () => {
  // Global test cleanup
  console.log('Cleaning up test environment...');
});

