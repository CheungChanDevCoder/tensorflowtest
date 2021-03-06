import tensorflow as tf
from tensorflow.examples.tutorials.mnist import input_data

"""
综合运用第4章介绍的方法。在调整神经网络的结构方面运用加隐藏层、使用激活函数；在神经网络优化时使用指数衰减的学习率，加入正则化的
损失函数，滑动平均模型。结果表明在4000轮以后因为梯度本身就很小所以参数改变变慢了，此示例中使用调整神经网络结构的方式（加隐藏层，
使用激活函数）优化效果明显，而使用神经网络优化（使用衰减的学习率，使用滑动平均模型）优化效果不太明显。但是问题复杂时，迭代不会
这么快收敛，这时使用指数衰减的学习率和滑动平均模型就可以发挥更大作用。不使用正则化只是用交叉熵在训练数据上正确率更高但是在测试
数据上更低，原因是出现了过拟合问题。
"""
# MNIST 数据集相关的常数
INPUT_NODE = 784  # 输入的节点数。对于MNIST数据集，这个就等于图片的像素。
OUTPUT_NODE = 10  # 输出的节点数，这个等于类别的数目。因为需要区分0-9所以节点数为10

# 配置神经网络的参数。
LAYER1_NODE = 500  # 隐藏层节点数。这里使用只有一个隐藏层的网络结构作为样例。这个隐藏层有500个节点。
BATCH_SIZE = 100  # 一个训练batch中的训练数据个数。数字越小时，训练过程越接近随机梯度下降；数字越大时，训练越接近梯度下降。
LEARNING_RATE_BASE = 0.8  # 基础的学习率
LEARNING_RATE_DECAY = 0.99  # 学习率的衰减率。
REGULARIZATION_RATE = 0.0001  # 描述模型复杂度的正则化项在损失函数中的系数。
TRAINIG_STEPS = 30000  # 训练轮数
MOVING_AVERAGE_DECAY = 0.99  # 滑动平均衰减率


# 定义一个辅助函数，给定神经网络的输入和所有参数，计算神经网络的前向传播结果。在这里定义了一个使用ReLU激活函数的三层全连接神经网络。
# 通过加入隐藏层实现了多层网络结构，通过ReLU激活函数实现了去线性化。在这个函数中也支持传入用于计算参数平均值的类，这样方便在测试时
# 使用滑动平均模型
def inference(input_tensor, avg_class, weights1, biases1, weights2, biases2):
    # 当没有提供滑动平均类时，直接使用参数当前的取值。
    if avg_class == None:
        # 计算隐藏层的前向传播结果，这里使用了ReLU激活函数。
        layer1 = tf.nn.relu(tf.matmul(input_tensor, weights1) + biases1)
        # 计算输出层的前向传播结果。因为在计算损失函数时会一并计算softmax函数，所以这里不需要加入激活函数。而且不加入softmax不会影响
        # 预测结果。因为预测时使用的是不同类别对应节点输出值的相对大小，有没有softmax层对最后分类结果计算没有影响。于是在计算整个神经
        # 网络的前向传播时可以不加入最后的softmax层。
        return tf.matmul(layer1, weights2) + biases2
    else:
        # 首先使用avg_class.average函数计算得到变量的滑动平均值，然后再进算相应的神经网络前向传播效果。
        layer1 = tf.nn.relu(tf.matmul(input_tensor, avg_class.average(weights1)) + avg_class.average(biases1))
        return tf.matmul(layer1, avg_class.average(weights2)) + avg_class.average(biases2)


# 训练模型的过程
def train(mnist):
    x = tf.placeholder(tf.float32, [None, INPUT_NODE], name='x-input')
    y_ = tf.placeholder(tf.float32, [None, OUTPUT_NODE], name='y-input')

    # 生成隐藏层的参数
    weights1 = tf.Variable(tf.truncated_normal([INPUT_NODE, LAYER1_NODE], stddev=0.1))
    biases1 = tf.Variable(tf.constant(0.1, shape=[LAYER1_NODE]))

    # 生成输出层的参数
    weights2 = tf.Variable(tf.truncated_normal([LAYER1_NODE, OUTPUT_NODE], stddev=0.1))
    biases2 = tf.Variable(tf.constant(0.1, shape=[OUTPUT_NODE]))

    # 计算在当前参数下的神经网络前向传播的结果。这里给出的用于计算滑动平均的类为None，所以函数不会使用参数的滑动平均值。
    y = inference(x, None, weights1, biases1, weights2, biases2)

    # 定义存储训练轮数的变量。这个变量不需要计算滑动平均值，所以这里指定这个变量为不可训练的变量(trainable=False)。在使用TensorFlow
    # 训练神经网络时，一般会将代表训练轮数的变量指定为不可训练的参数。
    global_step = tf.Variable(0, trainable=False)

    # 给定滑动平均衰减率和训练轮数的变量，初始化滑动平均类，给定训练轮数的变量可以加快训练早期变量的更新速度。
    variable_averages = tf.train.ExponentialMovingAverage(MOVING_AVERAGE_DECAY, global_step)

    # 在所有代表神经网络参数的变量上使用滑动平均。其他辅助变量（比如global_step）就不需要了。tf.trainable_variables返回的就是图
    # 上集合GraphKeys.TRAINABLE_VARIABLES中的元素。这个集合的元素就是所有没有指定trainable=False的参数。
    variable_averages_op = variable_averages.apply(tf.trainable_variables())

    # 计算了滑动平均之后的前向传播结果。第4章介绍过滑动平均不会改变变量本身的取值，而是会维护一个影子变量来记录其滑动平均值，所以当需
    # 要使用这个滑动平均值时，需要明确使用average函数。
    average_y = inference(x, variable_averages, weights1, biases1, weights2, biases2)

    # 计算交叉熵作为刻画预测值和真实值之间差距的损失函数。这里使用了TensorFlow中提供的sparse_softmax_cross_entropy_with_logists
    # 函数来计算交叉熵。当分类问题只有一个正确答案时，可以使用这个函数来加速计算交叉熵损失。这个函数的第一个参数是神经网络不包括softmax
    # 层的前向传播结果，第二个是训练数据的正确答案。因为正确答案是一个长度为10的一维数组，而该函数需要提供一个正确答案的数字，所以要是用
    # tf.argmax函数来得到正确答案对应的类别编号。
    cross_entropy = tf.nn.sparse_softmax_cross_entropy_with_logits(logits=y, labels=tf.arg_max(y_, 1))
    # 计算当前batch中所有样例的交叉熵平均值。
    cross_entropy_mean = tf.reduce_mean(cross_entropy)

    # 计算L2正则化损失函数。
    regularizer = tf.contrib.layers.l2_regularizer(REGULARIZATION_RATE)
    # 计算模型的正则化损失。一般只计算神经网络边上权重的正则化损失，而不使用偏置项。
    regularization = regularizer(weights1) + regularizer(weights2)
    # 总损失等于交叉熵损失和正则化损失的和。
    loss = cross_entropy_mean + regularization
    # 设置指数衰减的学习率。
    learning_rate = tf.train.exponential_decay(
        LEARNING_RATE_BASE,  # 基础的学习率，随着迭代的进行，更新变量时使用的学习率在这个基础上递减。
        global_step,  # 当前迭代的轮数。
        mnist.train.num_examples / BATCH_SIZE,  # 过完所有的训练数据需要的迭代次数。
        LEARNING_RATE_DECAY  # 学习率衰减速度。
    )
    # 使用tf.train.GradientDescentOptinizer优化算法来优化损失函数。注意这里损失函数包含了交叉熵损失和L2正则化损失。
    train_step = tf.train.GradientDescentOptimizer(learning_rate).minimize(loss, global_step=global_step)

    # 在训练神经网络模型时，每过一遍数据都需要通过反向传播来更新神经网络中的参数。又要更新每一个参数的滑动平均值。为了一次性操作，
    # TensorFlow提供了tf.control_dependencies和tf.group两种机制，下面两行程序和
    # train_op = tf.group(train_step, variable_averages_op)是等价的。
    with tf.control_dependencies([train_step, variable_averages_op]):
        train_op = tf.no_op(name="train")

    # 检验使用了滑动平均模型的神经网络前向传播结果是否正确。tf.argmax(average_y,1)计算每一个样例的预测答案。其中average_y是一个
    # batch_size * 10的二维数组，每一行表示一个样例的前向传播结果。tf.argmax的第二个参数“1”表示选取最大值的操作尽在第一个维度中
    # 进行。也就是说，只在每一选取最大值对应的下标。于是得到的结果是一个长度为batch的一维数组。这个一维数组中的值就表示了每一个样例
    # 对应的数字识别结果。tf.equal判断两个张量的每一维是否相等，如果相等返回True，否则返回False
    correct_protection = tf.equal(tf.arg_max(average_y, 1), tf.arg_max(y_, 1))
    # 这个运算首先将一个布尔值的数值转换为实数型，然后计算平均值。这个平均值就是模型在这一组数据中的正确率
    accuracy = tf.reduce_mean(tf.cast(correct_protection, tf.float32))

    # 初始化会话并开始训练过程
    with tf.Session() as sess:
        tf.global_variables_initializer().run()
        # 准备验证数据。一般在神经网络的训练过程中会通过验证数据来大致判断停止的条件和评判训练的结果。
        validate_feed = {x: mnist.validation.images,
                         y_: mnist.validation.labels}
        # 准备测试数据。在真实的应用中，这部分数据在训练时是不可见的，这个数据只是作为模型优劣的最终评价标准。
        test_feed = {x: mnist.test.images, y_: mnist.test.labels}

        # 迭代的训练神经网络。
        for i in range(TRAINIG_STEPS):
            # 每1000轮输出一次在验证数据集上的测试结果。
            if i % 1000 == 0:
                # 计算滑动平均模型在验证数据上的结果。因为MNIST数据集比较小，所以一次可以处理所有的验证数据。为了计算方便，本样例程序
                # 没有将验证数据划分为更小的batch。当神经网络模型比较复杂或者验证数据比较大时，太大的batch会导致计算时间过长甚至发生
                # 内存溢出的错误。
                validate_acc = sess.run(accuracy, feed_dict=validate_feed)
                print(f"After {i} training step(s), validation accuracy using average model is {validate_acc}")
                # test_acc = sess.run(accuracy, feed_dict=test_feed)
                # print(f"After {i} training step(s), test accuracy using average model is {test_acc}")
            # 产生这一轮使用一个batch的训练数据，并运行训练过程。
            xs, ys = mnist.train.next_batch(BATCH_SIZE)
            sess.run(train_op, feed_dict={x: xs, y_: ys})
        # 在训练结束之后，在测试数据上检验神经网络模型的最终正确率。
        test_acc = sess.run(accuracy, feed_dict=test_feed)
        print(f"After {TRAINIG_STEPS} training step(s), test accuracy using average model is {test_acc}")


# 主程序入口
def main(argb=None):
    # 声明处理MNIST数据集的类，这个类在初始化时，会自动下载数据。
    mnist = input_data.read_data_sets(r"D:\tmp", one_hot=True)
    train(mnist)


# TensorFlow提供了一个主程序入口，tf.app.run会调用上面定义的main函数。
if __name__ == '__main__':
    tf.app.run()
