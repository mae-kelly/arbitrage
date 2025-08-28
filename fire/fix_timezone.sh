#!/bin/bash
echo "Fixing timezone issues..."
find . -name "*.py" -type f -exec sed -i '' 's/timezone\.UTC/timezone.utc/g' {} +
find . -name "*.py" -type f -exec sed -i '' 's/datetime\.UTC/timezone.utc/g' {} +
echo "✓ Timezone fixed"
