from sklearn.metrics import accuracy_score

y_true = [1, 0, 1, 0]
y_pred = [1, 0, 0, 0]
accuracy = accuracy_score(y_true, y_pred)
print(f"准确率: {accuracy}")