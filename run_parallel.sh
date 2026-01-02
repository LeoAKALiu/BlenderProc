#!/bin/bash
# Parallel BlenderProc Rendering Script - Single Process Per Image
# This script runs multiple BlenderProc instances in parallel, each generating one image
# Each process is completely independent, ensuring clean memory and GPU state
# 
# Usage:
#   ./run_parallel.sh [num_parallel] [total_images] [output_dir] [base_seed]
#
# Example:
#   ./run_parallel.sh 2 20 output/dataset 1000
#
# Note: For M3 Pro, 2 parallel processes is recommended to avoid memory issues

# Don't use set -e - we want to handle errors manually in wait_for_slot
# set -e  # Exit on error

# Configuration
PARALLEL_JOBS=${1:-2}        # Number of parallel processes (default: 2 for M3 Pro)
TOTAL_IMAGES=${2:-20}         # Total number of images to generate
OUTPUT_DIR=${3:-"output/dataset"}  # Output directory (all images go here)
BASE_SEED=${4:-1000}          # Base seed (each image gets base_seed + image_index)
SCRIPT_NAME="generate_mountainous_solar_site.py"

echo "=========================================="
echo "Parallel BlenderProc Rendering"
echo "Single Process Per Image Mode"
echo "=========================================="
echo "Parallel jobs: $PARALLEL_JOBS"
echo "Total images: $TOTAL_IMAGES"
echo "Output directory: $OUTPUT_DIR"
echo "Base seed: $BASE_SEED"
echo "=========================================="
echo ""

# Check if script exists
if [ ! -f "$SCRIPT_NAME" ]; then
    echo "Error: Script '$SCRIPT_NAME' not found!"
    exit 1
fi

# Create output directories
mkdir -p "$OUTPUT_DIR/images"
mkdir -p "$OUTPUT_DIR/labels"

# Array to track running jobs
declare -a PIDS=()
declare -a IMAGE_INDICES=()
IMAGE_COUNTER=0

# Function to wait for a job slot
wait_for_slot() {
    while [ ${#PIDS[@]} -ge $PARALLEL_JOBS ]; do
        # Check which jobs are still running
        NEW_PIDS=()
        NEW_INDICES=()
        for i in "${!PIDS[@]}"; do
            PID=${PIDS[$i]}
            # Use local variable to avoid overwriting loop variable IMG_IDX
            CURRENT_IMG_IDX=${IMAGE_INDICES[$i]}
            if kill -0 $PID 2>/dev/null; then
                # Process still running
                NEW_PIDS+=($PID)
                NEW_INDICES+=($CURRENT_IMG_IDX)
            else
                # Process finished - wait to get exit code (suppress error if already waited)
                if wait $PID 2>/dev/null; then
                    EXIT_CODE=0
                else
                    EXIT_CODE=$?
                fi
                if [ $EXIT_CODE -eq 0 ]; then
                    echo "✓ Image ${CURRENT_IMG_IDX} completed (PID $PID)"
                else
                    echo "✗ Image ${CURRENT_IMG_IDX} failed (PID $PID, exit code $EXIT_CODE)"
                fi
            fi
        done
        PIDS=("${NEW_PIDS[@]}")
        IMAGE_INDICES=("${NEW_INDICES[@]}")
        
        # If still at capacity, wait a bit
        if [ ${#PIDS[@]} -ge $PARALLEL_JOBS ]; then
            sleep 0.5
        fi
    done
}

# Generate all images
echo "Starting image generation..."
echo ""

for IMG_IDX in $(seq 0 $((TOTAL_IMAGES - 1))); do
    # Wait for an available slot
    wait_for_slot
    
    # Calculate seed for this image
    SEED=$((BASE_SEED + IMG_IDX))
    
    # Log file for this image (format: image_000000.log)
    LOG_FILE="${OUTPUT_DIR}/image_$(printf "%06d" $IMG_IDX).log"
    
    echo "Starting image $IMG_IDX (seed=$SEED, PID will be logged)"
    
    # Run BlenderProc in background (single image per process)
    blenderproc run "$SCRIPT_NAME" "$OUTPUT_DIR" \
        --image_index "$IMG_IDX" \
        --seed "$SEED" \
        --use_clusters \
        --use_gpu \
        --max_samples 50 \
        --noise_threshold 0.01 \
        > "$LOG_FILE" 2>&1 &
    
    PID=$!
    PIDS+=($PID)
    IMAGE_INDICES+=($IMG_IDX)
    IMAGE_COUNTER=$((IMAGE_COUNTER + 1))
    
    echo "  Image $IMG_IDX started with PID: $PID"
done

# Wait for all remaining jobs to complete
echo ""
echo "All $TOTAL_IMAGES images started. Waiting for completion..."
echo ""

FAILED=0
for i in "${!PIDS[@]}"; do
    PID=${PIDS[$i]}
    # Use different variable name to avoid confusion
    FINAL_IMG_IDX=${IMAGE_INDICES[$i]}
    if wait $PID; then
        echo "✓ Image ${FINAL_IMG_IDX} completed (PID $PID)"
    else
        echo "✗ Image ${FINAL_IMG_IDX} failed (PID $PID)"
        FAILED=$((FAILED + 1))
    fi
done

echo ""
echo "=========================================="
if [ $FAILED -eq 0 ]; then
    echo "✓ All images completed successfully!"
    echo "Total images: $TOTAL_IMAGES"
    echo "Output directory: $OUTPUT_DIR"
    echo "  - Images: $OUTPUT_DIR/images/"
    echo "  - Labels: $OUTPUT_DIR/labels/"
else
    echo "✗ $FAILED image(s) failed. Check logs in $OUTPUT_DIR/image_*.log"
    exit 1
fi
echo "=========================================="
