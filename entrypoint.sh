#!/bin/bash

# Migrate old data files to data/ folder if they exist
for f in *_weights.json; do
    if [ -f "$f" ] && [ ! -f "data/$f" ]; then
        echo "Migrating $f to data/"
        mv "$f" "data/"
    fi
done

if [ -f "workout_cards.json" ] && [ ! -f "data/workout_cards.json" ]; then
    echo "Migrating workout_cards.json to data/"
    mv workout_cards.json data/
fi

# Create data directory if it doesn't exist
mkdir -p data

exec python -m bot