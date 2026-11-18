import { globalIgnores } from 'eslint/config';
import tsParser from '@typescript-eslint/parser';

export default [
  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: { parser: tsParser },
    rules: {},
  },
  globalIgnores(['.next/**', 'node_modules/**', 'next-env.d.ts']),
];
