import mlflow
from pathlib import Path
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier

root = Path.cwd().resolve()
mlruns = root / 'mlruns'
mlruns.mkdir(exist_ok=True)
mlflow.set_tracking_uri(f'sqlite:///{(mlruns / "mlflow.db").as_posix()}')
mlflow.set_experiment('ridewise-churn-prediction')

feature_columns = ['recency','frequency','monetary','avg_fare','tenure','avg_surge','max_surge','tip_rate','trips_per_week','avg_duration','distinct_drivers','weekend_ratio','night_ratio','card_ratio','sessions_count','avg_time_on_app','avg_pages','conversion_rate','age','avg_rating_given','loyalty_rank','was_referred']
df = pd.read_csv(root / 'data' / 'analytics_table.csv')
X = df[feature_columns].fillna(0)
y = df['churn']
X_train, _, y_train, _ = train_test_split(X, y, test_size=0.25, stratify=y, random_state=42)

with mlflow.start_run(run_name='smoke-test') as run:
    mlflow.log_params({'random_state': 42, 'test_size': 0.25})
    LogisticRegression(max_iter=2000, class_weight='balanced', C=0.5).fit(StandardScaler().fit_transform(X_train), y_train)
    mlflow.log_params({'lr_model_family':'logistic_regression','lr_C':0.5})
    RandomForestClassifier(n_estimators=5, max_depth=3, min_samples_leaf=2, class_weight='balanced', random_state=42, n_jobs=-1).fit(X_train, y_train)
    mlflow.log_params({'rf_model_family':'random_forest','rf_n_estimators':5})
    print('run_id', run.info.run_id)
