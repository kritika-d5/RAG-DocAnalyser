// Shared backend settings and the demo sample document.
export const API_BASE = import.meta.env.VITE_API_BASE_URL;

export const SAMPLE_DOCUMENT = {
  url: '/sample/northwind-renewables-annual-report-2025.txt',
  filename: 'northwind-renewables-annual-report-2025.txt',
  questions: [
    'How much did revenue grow in 2025?',
    'Which segment grew fastest?',
    'What went wrong with Delta Valley?',
    'What are the main risks?',
    'What is the outlook for 2026?',
  ],
};
