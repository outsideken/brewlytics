# brewlytics

This Github repository is for the brewlytics Python Script functional. These scripts demonstrate different analytic tasks using Python.

* brewlytics API
  * Machine Learning
    * sklearn DecisionTree

<hr>

## [brewlytics Model - Scikit-learn DecisonTreeClassifier - Ellipse Classifier](https://demo.brewlytics.com/app/#/build/4e6c1944-328a-47dc-b1cd-119b5101f61d)

* [sklearn: DecisionTreeClassifier](https://scikit-learn.org/stable/modules/generated/sklearn.tree.DecisionTreeClassifier.html#sklearn.tree.DecisionTreeClassifier)
* [sklearn.metrics.classification_report](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.classification_report.html?highlight=classification%20report#sklearn.metrics.classification_report)
* [sklearn.metrics.confusion_matrix](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.confusion_matrix.html?highlight=confusion_matrix#sklearn.metrics.confusion_matrix)
* [sklearn.metrics.accuracy_score](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.accuracy_score.html?highlight=accuracy_score#sklearn.metrics.accuracy_score)
* [sklearn.metrics.roc_curve](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.roc_curve.html?highlight=roc_curve#sklearn.metrics.roc_curve)
* [sklearn.metrics.roc_auc_score](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.roc_auc_score.html?highlight=roc_auc_score#sklearn.metrics.roc_auc_score)

This brewlytics model uses the Python Script (Beta) functional to demonstrate how a Scikit-learn DecisionTree machine learning algorithm can be setup using the new Machine Learnine Runtime environment. This example uses a synthetic ellipse dataset that was randomly created for latitude, longitude, semi-major axis, and semi-minor axis. The ellipse eccentricity and area were calculated using Python in a seperate brewlytics model. 

This model is an attempt to redfine how confidence error-ellipses are evaluated for geolocation accuracy.

The DecisionTree features columns are model user-provided inputs that include eccentricity and area. The target for this dataset was created by setting a semi-minor axis threshold value of equal to or less than 5.1 nautical miles as a "good" ellipse, and those with a semi-minor axis greater than 5.1 nautical miles as a "bad" ellipse. 

This specific model uses GitHub as a Python script repository to provide a version control and tracking for code changes.

