# apps/analytics/ml_predictor.py - COMPLETE FINAL VERSION

import joblib
import numpy as np
import pandas as pd
from django.conf import settings
import os

class RiskPredictor:
    def __init__(self):
        self.model_path = os.path.join(settings.BASE_DIR, 'ml_models', 'std_risk_model.pkl')
        self.pipeline = None
        self.load_model()
    
    def load_model(self):
        """Load GridSearchCV model and extract best pipeline"""
        try:
            loaded = joblib.load(self.model_path)
            
            # GridSearchCV result - get best estimator
            if hasattr(loaded, 'best_estimator_'):
                self.pipeline = loaded.best_estimator_
                print("✅ ML Model loaded from GridSearchCV")
                print(f"   Best score: {loaded.best_score_:.4f}")
                print(f"   Best params: {loaded.best_params_}")
            else:
                self.pipeline = loaded
                print("✅ ML Pipeline loaded directly")
            
            # Show pipeline structure
            if hasattr(self.pipeline, 'named_steps'):
                print(f"   Pipeline steps: {list(self.pipeline.named_steps.keys())}")
                
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            self.pipeline = None
    
    def predict_risk(self, quiz_avg, assignment_avg, attendance_rate, gender=1):
        """
        Predict student risk using ML pipeline
        
        Input format: [[gender, quiz_avg, assignment_avg, attendance_rate]]
        Example: [[1, 80, 76, 70]]
        
        Returns: dict with risk prediction
        """
        if self.pipeline is None:
            return self._fallback_prediction(quiz_avg, assignment_avg, attendance_rate)
        
        try:
            # Prepare input - pipeline expects this format
            input_data = [[gender, quiz_avg, assignment_avg, attendance_rate]]
            
            print(f"📊 Input: [gender={gender}, quiz={quiz_avg}, assign={assignment_avg}, attend={attendance_rate}]")
            
            # Pipeline automatically scales and predicts
            prediction = self.pipeline.predict(input_data)[0]
            print(f"🔮 Prediction: {prediction} (type: {type(prediction)})")
            
            # Convert string prediction to risk value
            prediction_value, base_risk = self._convert_prediction(prediction)
            
            # Get probability if available
            risk_score = self._get_risk_score(input_data, base_risk)
            
            # Determine risk level
            risk_level, color = self._get_risk_level(risk_score)
            
            # Generate feedback
            feedback = self._generate_feedback(quiz_avg, assignment_avg, attendance_rate, risk_level)
            
            return {
                'risk_score': round(float(risk_score), 2),
                'risk_level': risk_level,
                'risk_color': color,
                'feedback': feedback,
                'prediction': prediction_value,
                'model_used': True
            }
            
        except Exception as e:
            print(f"❌ Prediction error: {e}")
            import traceback
            traceback.print_exc()
            return self._fallback_prediction(quiz_avg, assignment_avg, attendance_rate)
    
    def _convert_prediction(self, prediction):
        """
        Convert model prediction to risk value
        
        Model outputs: 'Low', 'Medium', 'High' (strings)
        Returns: (prediction_int, risk_base_score)
        """
        if isinstance(prediction, str):
            pred_lower = prediction.lower().strip()
            
            if pred_lower in ['high', 'high risk']:
                return 1, 0.8  # High risk
            elif pred_lower in ['medium', 'medium risk', 'moderate']:
                return 1, 0.5  # Medium risk (still at risk)
            elif pred_lower in ['low', 'low risk']:
                return 0, 0.2  # Low risk
        
        # Fallback for numeric predictions
        if isinstance(prediction, (int, np.integer)):
            if prediction >= 2:
                return 1, 0.8  # High
            elif prediction == 1:
                return 1, 0.5  # Medium
            else:
                return 0, 0.2  # Low
        
        # Default
        print(f"⚠️ Unknown prediction format: {prediction}")
        return 0, 0.3
    
    def _get_risk_score(self, input_data, base_risk):
        """Get risk probability score"""
        try:
            if hasattr(self.pipeline, 'predict_proba'):
                proba = self.pipeline.predict_proba(input_data)[0]
                print(f"📈 Probabilities: {proba}")
                
                # If model gives probabilities for each class
                if len(proba) >= 3:  # [Low, Medium, High]
                    # Combine Medium and High as "at risk"
                    risk_score = proba[1] + proba[2]
                elif len(proba) == 2:
                    risk_score = proba[1]
                else:
                    risk_score = base_risk
            else:
                risk_score = base_risk
            
            return risk_score
            
        except Exception as e:
            print(f"⚠️ Error getting probability: {e}")
            return base_risk
    
    def _get_risk_level(self, risk_score):
        """Determine risk level and color from score"""
        if risk_score >= 0.65:
            return 'HIGH RISK', 'red'
        elif risk_score >= 0.35:
            return 'MEDIUM RISK', 'orange'
        else:
            return 'LOW RISK', 'green'
    
    def _generate_feedback(self, quiz_avg, assignment_avg, attendance_rate, risk_level):
        """Generate personalized feedback (NO LAB MESSAGES)"""
        feedback_parts = []
        
        # Specific advice based on weak areas
        if attendance_rate < 75:
            feedback_parts.append('Improve attendance')
        if assignment_avg < 70:
            feedback_parts.append('Complete assignments')
        if quiz_avg < 70:
            feedback_parts.append('Study for quizzes')
        
        # If no specific issues but still at risk
        if not feedback_parts and risk_level != 'LOW RISK':
            feedback_parts.append('Maintain consistent effort')
        
        # Success message
        if not feedback_parts:
            return 'Keep up the excellent work!'
        
        return ' and '.join(feedback_parts)
    
    def _fallback_prediction(self, quiz_avg, assignment_avg, attendance_rate):
        """Fallback if model fails"""
        print("⚠️ Using fallback prediction")
        
        # Weighted average
        overall = (quiz_avg * 0.35 + assignment_avg * 0.35 + attendance_rate * 0.30)
        
        # Calculate risk
        risk_score = (100 - overall) / 100
        
        if risk_score >= 0.6:
            risk_level = 'HIGH RISK'
            color = 'red'
            prediction = 1
        elif risk_score >= 0.3:
            risk_level = 'MEDIUM RISK'
            color = 'orange'
            prediction = 1
        else:
            risk_level = 'LOW RISK'
            color = 'green'
            prediction = 0
        
        feedback = self._generate_feedback(quiz_avg, assignment_avg, attendance_rate, risk_level)
        
        return {
            'risk_score': round(float(risk_score), 2),
            'risk_level': risk_level,
            'risk_color': color,
            'feedback': feedback,
            'prediction': prediction,
            'model_used': False
        }

# Create singleton instance
ml_predictor = RiskPredictor()