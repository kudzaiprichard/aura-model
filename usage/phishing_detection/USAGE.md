# Phishing Detection Pipeline - Usage Guide

## Overview

This package provides a **stateless, scalable pipeline** for phishing email detection with support for:
- ✅ Multiple model versions running simultaneously
- ✅ Hot-swappable models (no restart needed)
- ✅ Incremental online learning
- ✅ Thread-safe operations
- ✅ Active model management

---

## Quick Start

### 1. Basic Prediction

```python
from preprocessing.cleaner import EmailCleaner
from preprocessing.features import EmailFeatureExtractor
from pipelines.prediction import PredictionPipeline

# Initialize components (reusable across pipelines)
cleaner = EmailCleaner(verbose=False)
extractor = EmailFeatureExtractor(
    subject_vectorizer_path='artifacts/pipeline_components/subject_vectorizer.pkl',
    body_vectorizer_path='artifacts/pipeline_components/body_vectorizer.pkl',
    verbose=False
)

# Create prediction pipeline
pipeline = PredictionPipeline(
    model_path='artifacts/v1_2/production/phishing_detector_mlp_classifier.pkl',
    cleaner=cleaner,
    feature_extractor=extractor,
    threshold=75.0,
    verbose=False
)

# Predict single email
result = pipeline.predict(
    sender='sender@example.com',
    subject='Email subject',
    body='Email body content...'
)

print(f"Prediction: {result.predicted_label}")
print(f"Confidence: {result.confidence_score * 100:.1f}%")
print(f"Should Alert: {result.should_alert}")
```

### 2. Batch Prediction

```python
emails = [
    {'sender': 'alice@company.com', 'subject': 'Meeting', 'body': 'Hi team...'},
    {'sender': 'bob@phish.xyz', 'subject': 'URGENT!!!', 'body': 'Click here...'}
]

results = pipeline.predict_batch(emails)

for i, result in enumerate(results):
    print(f"Email {i+1}: {result.predicted_label}")
```

---

## Multi-Model Testing

**Test multiple model versions simultaneously** without interference:

```python
from pipelines.prediction import PredictionPipeline

# Create separate pipelines for different artifacts
pipeline_v1_0 = PredictionPipeline(
    model_path='artifacts/v1_0/production/phishing_detector_mlp_classifier.pkl',
    cleaner=cleaner,
    feature_extractor=extractor,
    threshold=75
)

pipeline_v1_1 = PredictionPipeline(
    model_path='artifacts/v1_1/production/phishing_detector_mlp_classifier.pkl',
    cleaner=cleaner,
    feature_extractor=extractor,
    threshold=75
)

pipeline_v1_2 = PredictionPipeline(
    model_path='artifacts/v1_2/production/phishing_detector_mlp_classifier.pkl',
    cleaner=cleaner,
    feature_extractor=extractor,
    threshold=75
)

# Test same email against all artifacts
email = {'sender': '...', 'subject': '...', 'body': '...'}

result_v1_0 = pipeline_v1_0.predict(**email)
result_v1_1 = pipeline_v1_1.predict(**email)
result_v1_2 = pipeline_v1_2.predict(**email)

# Compare results
print(f"v1.0: {result_v1_0.predicted_label} (conf: {result_v1_0.confidence_score:.2f})")
print(f"v1.1: {result_v1_1.predicted_label} (conf: {result_v1_1.confidence_score:.2f})")
print(f"v1.2: {result_v1_2.predicted_label} (conf: {result_v1_2.confidence_score:.2f})")
```

**Key Point:** Each pipeline is completely independent. No caching, no interference.

---

## Model Registry (Active Model Management)

### Get Active Model

```python
from models.registry import ModelRegistry

registry = ModelRegistry(models_dir='artifacts')

# Get currently active model
active_version = registry.get_active_version()  # "v1_2"
active_paths = registry.get_active_model_paths()

print(f"Active model: {active_version}")
print(f"Model path: {active_paths['model']}")
```

### Set Active Model

```python
# Designate v1_2 as production model
registry.set_active_model('v1_2')

# Now create pipeline with active model
active_paths = registry.get_active_model_paths()
pipeline = PredictionPipeline(
    model_path=f"artifacts/{active_paths['model']}",
    cleaner=cleaner,
    feature_extractor=extractor
)
```

### List All Versions

```python
# Get all available versions
all_versions = registry.list_versions()
print(f"Available versions: {all_versions}")

# Get version details
info = registry.get_version_info('v1_2')
print(f"Accuracy: {info['performance_metrics']['accuracy']:.3f}")
print(f"Trained: {info['trained_timestamp']}")
```

---

## Online Learning (Model Updates)

**Create new model versions** from user corrections without retraining from scratch:

```python
from pipelines.training import OnlineLearningPipeline

# Create training pipeline
training_pipeline = OnlineLearningPipeline(
    base_model_path='artifacts/v1_0/production/phishing_detector_mlp_classifier.pkl',
    cleaner=cleaner,
    feature_extractor=extractor,
    output_dir='artifacts',
    verbose=False
)

# Prepare user corrections (labeled emails)
corrections = [
    {'sender': 'legitimate@company.com', 'subject': 'Meeting',
     'body': 'Hi team...', 'label': 0},  # 0 = legitimate

    {'sender': 'scam@phish.xyz', 'subject': 'URGENT!!!',
     'body': 'Click here...', 'label': 1}  # 1 = phishing
]

# Train and create new version
result = training_pipeline.partial_fit_batch(
    emails=corrections,
    parent_version='v1_0',  # Base version
    validate=True  # Validate performance before/after
)

if result.success:
    print(f"New version created: {result.version_number}")
    print(f"Emails processed: {result.emails_processed}")
    print(f"Accuracy before: {result.performance_before['accuracy']:.3f}")
    print(f"Accuracy after: {result.performance_after['accuracy']:.3f}")
else:
    print(f"Training failed: {result.error}")
```

**Result:** New model version (e.g., `v1_1`) is created. Original model (`v1_0`) remains untouched.

---

## Model Loading Utilities

### Load Model Components

```python
from models.loader import ModelLoader

loader = ModelLoader(verbose=True)

# Load model only
model = loader.load_model('./artifacts/v1_2/production/phishing_detector_mlp_classifier.pkl')

# Load vectorizers
subject_vec, body_vec = loader.load_vectorizers(
    subject_path='artifacts/pipeline_components/subject_vectorizer.pkl',
    body_path='artifacts/pipeline_components/body_vectorizer.pkl'
)

# Or load everything at once
model, subject_vec, body_vec = loader.load_pipeline_components(
    model_path='artifacts/v1_2/production/phishing_detector_mlp_classifier.pkl',
    subject_vectorizer_path='artifacts/pipeline_components/subject_vectorizer.pkl',
    body_vectorizer_path='artifacts/pipeline_components/body_vectorizer.pkl'
)
```

### Validate Model Compatibility

```python
# Check if model supports online learning
compatibility = loader.validate_model_compatibility(model)

if not compatibility['supports_partial_fit']:
    print("Warning: Model doesn't support online learning")
```

---

## Validation Utilities

```python
from utils.validation import (
    validate_email_fields,
    validate_training_batch,
    normalize_threshold
)

# Validate email inputs
is_valid, error = validate_email_fields(sender, subject, body)
if not is_valid:
    raise ValueError(error)

# Validate training batch
is_valid, error = validate_training_batch(corrections)
if not is_valid:
    raise ValueError(error)

# Normalize threshold (75 → 0.75)
threshold = normalize_threshold(75)
```

---

## Performance Metrics

```python
from utils.metrics import (
    calculate_all_metrics,
    compare_metrics,
    generate_performance_summary
)

# Calculate metrics
metrics = calculate_all_metrics(y_true, y_pred)
print(f"Accuracy: {metrics['accuracy']:.3f}")
print(f"Precision: {metrics['precision']:.3f}")
print(f"Recall: {metrics['recall']:.3f}")
print(f"F1 Score: {metrics['f1_score']:.3f}")

# Compare before/after
comparison = compare_metrics(metrics_before, metrics_after)
print(f"Accuracy change: {comparison['accuracy']['change_percent']:.1f}%")

# Generate comprehensive summary
summary = generate_performance_summary(y_true, y_pred, probabilities)
```

---

## Best Practices

### 1. Reuse Components
```python
# ✅ GOOD: Create once, reuse across pipelines
cleaner = EmailCleaner()
extractor = EmailFeatureExtractor(...)

pipeline1 = PredictionPipeline(model_path='v1_0/...', cleaner=cleaner, feature_extractor=extractor)
pipeline2 = PredictionPipeline(model_path='v1_1/...', cleaner=cleaner, feature_extractor=extractor)

# ❌ BAD: Creating new instances every time (wasteful)
pipeline1 = PredictionPipeline(model_path='v1_0/...', cleaner=EmailCleaner(), ...)
pipeline2 = PredictionPipeline(model_path='v1_1/...', cleaner=EmailCleaner(), ...)
```

### 2. Hot-Swap Models

```python
# Switch artifacts without creating new pipeline
pipeline.model_path = 'artifacts/v1_2/production/phishing_detector_mlp_classifier.pkl'
pipeline.reload_model()  # Reload from disk
```

### 3. Use Model Registry

```python
# ✅ GOOD: Use registry for version management
registry = ModelRegistry()
active_paths = registry.get_active_model_paths()
pipeline = PredictionPipeline(model_path=f"artifacts/{active_paths['model']}", ...)

# ❌ BAD: Hardcoding paths
pipeline = PredictionPipeline(model_path='artifacts/v1_2/production/...', ...)
```

### 4. Validate Inputs
```python
# Always validate before processing
is_valid, error = validate_email_fields(sender, subject, body)
if not is_valid:
    return {"error": error}

result = pipeline.predict(sender, subject, body)
```

### 5. Handle Errors Gracefully
```python
try:
    result = pipeline.predict(sender, subject, body)
    
    if result.error:
        # Prediction failed
        print(f"Error: {result.error}")
    else:
        # Process successful result
        print(f"Prediction: {result.predicted_label}")
        
except Exception as e:
    print(f"Pipeline error: {str(e)}")
```

---

## Common Patterns

### Pattern 1: A/B Testing Models
```python
# Compare two artifacts on same dataset
pipeline_old = PredictionPipeline(model_path='v1_0/...', ...)
pipeline_new = PredictionPipeline(model_path='v1_1/...', ...)

for email in test_emails:
    result_old = pipeline_old.predict(**email)
    result_new = pipeline_new.predict(**email)
    
    # Compare predictions
    if result_old.predicted_label != result_new.predicted_label:
        print(f"Disagreement: old={result_old.predicted_label}, new={result_new.predicted_label}")
```

### Pattern 2: Continuous Learning Loop
```python
# Collect corrections from users
corrections = []

# User corrects a prediction
corrections.append({
    'sender': email.sender,
    'subject': email.subject,
    'body': email.body,
    'label': user_corrected_label
})

# Once enough corrections collected (e.g., 50+)
if len(corrections) >= 50:
    training_pipeline = OnlineLearningPipeline(...)
    result = training_pipeline.partial_fit_batch(corrections)
    
    if result.success:
        # New version created, optionally set as active
        registry.set_active_model(result.version_number)
```

### Pattern 3: Multi-User Testing

```python
# Each user can test different artifacts independently
def get_user_pipeline(user_id):
    # User A tests v1_0
    if user_id == "user_a":
        return PredictionPipeline(model_path='v1_0/...', ...)

    # User B tests v1_1
    elif user_id == "user_b":
        return PredictionPipeline(model_path='v1_1/...', ...)

    # Others use active model
    else:
        registry = ModelRegistry()
        active_paths = registry.get_active_model_paths()
        return PredictionPipeline(model_path=f"artifacts/{active_paths['model']}", ...)


# Each user gets independent pipeline
pipeline = get_user_pipeline(current_user_id)
result = pipeline.predict(...)
```

---

## File Structure

```
models/
├── model_metadata.json              # Central version registry
├── pipeline_components/
│   ├── subject_vectorizer.pkl       # Shared across all versions
│   └── body_vectorizer.pkl          # Shared across all versions
├── v1_0/
│   └── production/
│       └── phishing_detector_mlp_classifier.pkl
├── v1_1/
│   └── production/
│       └── phishing_detector_mlp_classifier.pkl
└── v1_2/
    └── production/
        └── phishing_detector_mlp_classifier.pkl
```

---

## Troubleshooting

### Issue: Model not loading
```python
# Validate file exists
from utils.validation import validate_file_exists

is_valid, error = validate_file_exists(model_path, "Model file")
if not is_valid:
    print(f"File issue: {error}")
```

### Issue: Training fails
```python
# Check model supports partial_fit
from models.loader import ModelLoader

loader = ModelLoader()
model = loader.load_model(base_model_path)
compatibility = loader.validate_model_compatibility(model)

if not compatibility['supports_partial_fit']:
    print("Model doesn't support online learning!")
```

### Issue: Models getting cached
```python
# Each PredictionPipeline instance is independent
# If you see caching, you're reusing the same instance

# ✅ GOOD: Create new instance
pipeline1 = PredictionPipeline(model_path='v1_0/...', ...)
pipeline2 = PredictionPipeline(model_path='v1_1/...', ...)

# ❌ BAD: Reusing same instance
pipeline = PredictionPipeline(model_path='v1_0/...', ...)
pipeline.model_path = 'v1_1/...'  # Still uses v1_0 unless you call reload_model()
```

---

## Summary

**Key Capabilities:**
- ✅ **Stateless pipelines** - No hidden caching or shared state
- ✅ **Multi-model support** - Test multiple versions simultaneously
- ✅ **Hot-swappable** - Switch models without restart
- ✅ **Online learning** - Incremental updates without full retraining
- ✅ **Version management** - Track and manage all model versions
- ✅ **Thread-safe** - Safe for concurrent use

**Start Simple:**
1. Create `cleaner` and `extractor` (reuse these)
2. Create `PredictionPipeline` with model path
3. Call `predict()` on emails
4. Use `ModelRegistry` to manage versions
5. Use `OnlineLearningPipeline` for updates

**Need Help?** Check the examples in the `examples/` directory.